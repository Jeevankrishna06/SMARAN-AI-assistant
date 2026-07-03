import time
import numpy as np
import pyaudio
import queue
import threading
import speech_recognition as sr

# ==========================================
# CLAP CONFIGURATION 
# Adjust these values to tune sensitivity
# ==========================================
CLAP_MIN_SNR = 2.0             # Peak must be at least 2x louder than background noise (relaxed for quiet claps)
CLAP_MIN_PEAK_AMP = 40         # Minimum peak amplitude to process (extremely low for minimal claps)
CLAP_COOLDOWN = 2.0            # Ignore additional claps for X seconds after a wake
CLAP_MAX_RISE_TIME_MS = 50.0   # A clap rises extremely quickly
CLAP_MAX_DECAY_RATIO = 0.6     # Energy must decay rapidly
CLAP_MIN_ZCR = 0.01            # Zero crossing rate (lowered to 0.01 to support laptop microphone acoustics)
# ==========================================

class ClapClassifier:
    def __init__(self, sample_rate=16000):
        self.sample_rate = sample_rate
        
    def _ms_to_samples(self, ms):
        return int((ms / 1000.0) * self.sample_rate)
        
    def analyze_buffer(self, audio_array):
        """
        Analyzes a numpy array of audio samples (e.g. 0.5s duration) for a clap.
        Uses Signal-to-Noise Ratio (SNR) to allow extremely low-volume claps.
        """
        peak_idx = np.argmax(np.abs(audio_array))
        peak_amp = np.abs(audio_array[peak_idx])
        
        # We need at least 100ms before and 200ms after the peak in the buffer
        min_before = self._ms_to_samples(100)
        min_after = self._ms_to_samples(200)
        if peak_idx < min_before or peak_idx > (len(audio_array) - min_after):
            return False, {}
            
        # Calculate Background Noise (RMS of the first 50ms of the buffer, far from peak)
        bg_window = audio_array[:self._ms_to_samples(50)].astype(np.float32)
        bg_rms = np.sqrt(np.mean(bg_window**2)) + 1e-6
        
        # Peak RMS (+/- 3ms)
        peak_window_size = self._ms_to_samples(3)
        peak_window = audio_array[peak_idx-peak_window_size : peak_idx+peak_window_size].astype(np.float32)
        peak_rms = np.sqrt(np.mean(peak_window**2)) + 1e-6
        
        snr = peak_rms / bg_rms
        
        # 1. Quick SNR Check: Must be significantly louder than ambient silence, but ignores absolute volume
        if snr < CLAP_MIN_SNR or peak_amp < CLAP_MIN_PEAK_AMP:
            return False, {}
            
        # Rise Time: Go backwards until amplitude drops to 20% of peak
        start_idx = peak_idx
        threshold = max(bg_rms * 1.5, peak_amp * 0.2)
        search_limit = max(0, peak_idx - self._ms_to_samples(100))
        for i in range(peak_idx, search_limit, -1):
            if np.abs(audio_array[i]) < threshold:
                start_idx = i
                break
        rise_time_ms = ((peak_idx - start_idx) / self.sample_rate) * 1000.0
        
        # Decay Check: Compare peak RMS vs RMS 100ms-200ms later
        post_start = peak_idx + self._ms_to_samples(100)
        post_end = peak_idx + self._ms_to_samples(200)
        post_window = audio_array[post_start : post_end].astype(np.float32)
        post_rms = np.sqrt(np.mean(post_window**2))
        
        decay_ratio = post_rms / peak_rms
        
        # Zero Crossing Rate around peak (+/- 25ms)
        zcr_size = self._ms_to_samples(25)
        zcr_window = audio_array[peak_idx-zcr_size : peak_idx+zcr_size]
        zcr = np.sum(np.diff(np.sign(zcr_window)) != 0) / max(1, len(zcr_window))
        
        metrics = {
            "bg_rms": int(bg_rms),
            "peak": int(peak_amp),
            "snr": round(snr, 1),
            "rise_time_ms": round(rise_time_ms, 2),
            "decay_ratio": round(decay_ratio, 3),
            "zcr": round(zcr, 3)
        }
        
        is_clap = (
            snr >= CLAP_MIN_SNR and
            rise_time_ms < CLAP_MAX_RISE_TIME_MS and
            decay_ratio < CLAP_MAX_DECAY_RATIO and
            zcr > CLAP_MIN_ZCR
        )
            
        return is_clap, metrics

class BufferedMicSource(sr.Microphone):
    """
    Inherits directly from sr.Microphone to guarantee the exact same bulletproof
    hardware selection, PyAudio stream management, and dynamic sample rate as standard voice wake.
    """
    def __init__(self, on_clap_callback=None, check_active_callback=None, *args, **kwargs):
        # Initialize sr.Microphone which sets up self.device_index, self.CHUNK, etc.
        super().__init__(*args, **kwargs)
        self.on_clap_callback = on_clap_callback
        self.check_active_callback = check_active_callback
        
        # Intercept queue to pass data to speech_recognition unmodified
        self.audio_queue = queue.Queue()
        self.analysis_thread = None
        self.is_capturing = False
        self.last_clap_time = 0
        self.classifier = None
        
        self.buffer_lock = threading.Lock()
        self.rolling_buffer = None
        
    def __enter__(self):
        # Open standard sr.Microphone stream (automatically finds best sample rate!)
        super().__enter__()
        
        # Save the real PyAudio stream for our capture loop
        self.real_pyaudio_stream = self.stream
        
        # Replace self.stream so speech_recognition reads from our queue
        class QueueStreamProxy:
            def __init__(self, q):
                self.q = q
            def read(self, size, exception_on_overflow=False):
                return self.q.get()
        self.stream = QueueStreamProxy(self.audio_queue)
        
        # Initialize DSP with the dynamically chosen sample rate
        self.classifier = ClapClassifier(sample_rate=self.SAMPLE_RATE)
        
        # Create a rolling buffer large enough for 0.5 seconds of audio at this sample rate
        buffer_frames = int(self.SAMPLE_RATE * 0.5)
        self.rolling_buffer = np.zeros(buffer_frames, dtype=np.int16)
        
        self.is_capturing = True
        self.start_time = time.time()
        self.analysis_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.analysis_thread.start()
        return self
        
    def _capture_loop(self):
        while self.is_capturing:
            try:
                # Read from the REAL PyAudio stream
                data = self.real_pyaudio_stream.read(self.CHUNK)
                audio_chunk = np.frombuffer(data, dtype=np.int16)
                
                # Update 0.5s rolling buffer
                with self.buffer_lock:
                    self.rolling_buffer = np.roll(self.rolling_buffer, -len(audio_chunk))
                    self.rolling_buffer[-len(audio_chunk):] = audio_chunk
                    buffer_copy = self.rolling_buffer.copy()
                    
                # Put data into the queue so speech_recognition can read it!
                self.audio_queue.put(data)
                
                is_active = self.check_active_callback() if self.check_active_callback else False
                
                # Check for silence (all zeros) from the microphone
                new_chunk_peak = np.max(np.abs(audio_chunk))
                if new_chunk_peak == 0:
                    if not hasattr(self, 'zero_start_time'):
                        self.zero_start_time = time.time()
                    elif time.time() - self.zero_start_time > 3.0:
                        if time.time() - getattr(self, 'last_zero_warn', 0) > 5.0:
                            print("⚠️ [WARNING] Microphone stream is returning all zeros! Audio input may be blocked, locked, or muted.", flush=True)
                            self.last_zero_warn = time.time()
                else:
                    self.zero_start_time = None

                # Only run clap classification if not active AND we are past the 1.0s startup suppression window
                startup_elapsed = time.time() - getattr(self, 'start_time', time.time())
                
                if not is_active and startup_elapsed > 1.0:
                    # SUPER DEBUG - Detect ANY relative spike in audio
                    bg_rms = np.sqrt(np.mean(buffer_copy[:self.classifier._ms_to_samples(50)].astype(np.float32)**2)) + 1e-6
                    peak_idx = np.argmax(np.abs(buffer_copy))
                    peak_amp = np.abs(buffer_copy[peak_idx])
                    
                    if peak_idx > self.classifier._ms_to_samples(100):
                        peak_window = buffer_copy[peak_idx-50 : peak_idx+50].astype(np.float32)
                        peak_rms = np.sqrt(np.mean(peak_window**2)) + 1e-6
                        
                        if (peak_rms / bg_rms) > 2.0 and peak_amp > CLAP_MIN_PEAK_AMP:
                            if not hasattr(self, 'last_debug_time'):
                                self.last_debug_time = 0
                            if time.time() - self.last_debug_time > 0.5:
                                print(f"\n[DEBUG] Acoustic Spike Detected! Peak={peak_amp}, SNR={round(peak_rms/bg_rms, 1)}x background", flush=True)
                                self.last_debug_time = time.time()
                            
                    is_clap, metrics = self.classifier.analyze_buffer(buffer_copy)
                    
                    if metrics:
                        now = time.time()
                        wake_triggered = False
                        
                        if is_clap:
                            if now - self.last_clap_time > CLAP_COOLDOWN:
                                self.last_clap_time = now
                                wake_triggered = True
                                if self.on_clap_callback:
                                    self.on_clap_callback()
                        
                        print(f"\n[CLAP]", flush=True)
                        print(f"Background RMS: {metrics.get('bg_rms', 0)}", flush=True)
                        print(f"Peak: {metrics['peak']} (SNR: {metrics['snr']}x)", flush=True)
                        print(f"Clap Detected: {'YES' if is_clap else 'NO'} (Rise:{metrics['rise_time_ms']}ms, Decay:{metrics['decay_ratio']}, ZCR:{metrics['zcr']})", flush=True)
                        print(f"Wake Triggered: {'YES' if wake_triggered else 'NO'}", flush=True)
                        
            except Exception as e:
                print(f"BufferedMicSource FATAL ERROR: {e}")
                import traceback
                traceback.print_exc()
                break

    def __exit__(self, exc_type, exc_value, traceback):
        self.is_capturing = False
        if self.analysis_thread:
            self.analysis_thread.join(timeout=1.0)
            
        # Restore the real PyAudio stream so sr.Microphone can close it!
        if hasattr(self, 'real_pyaudio_stream'):
            self.stream = self.real_pyaudio_stream
            
        # Clean up PyAudio stream
        super().__exit__(exc_type, exc_value, traceback)
