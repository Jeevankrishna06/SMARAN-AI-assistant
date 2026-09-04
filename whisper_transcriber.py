import numpy as np
import speech_recognition as sr
import sys
import os
import requests
import io
import env_loader

# Configure stdout encoding to handle emojis on Windows console
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

class WhisperTranscriber:
    def __init__(self, model_size="base.en", device="cpu", compute_type="int8"):
        self.api_key = None
        self.model = "groq-stt"
        self.loading = False  # Instantly ready!
        
        self._load_config()

    def _load_config(self):
        """Load API key securely from environment variables"""
        self.api_key = (
            os.getenv("GROQ_AUDIO_API_KEY") or
            os.getenv("GROQ_API_KEY") or
            os.getenv("groq_api_key")
        )
        if self.api_key:
            self.api_key = self.api_key.strip()
            print("[WHISPER GROQ] Speech-to-Text engine initialized successfully.")
        else:
            print("[WHISPER GROQ] WARNING: GROQ_AUDIO_API_KEY or GROQ_API_KEY not set in environment.")

    def transcribe(self, audio_data: sr.AudioData, mode="accurate") -> str:
        """
        Transcribes SpeechRecognition's AudioData to text using Groq's STT API.
        Converts the audio data to WAV format in-memory.
        Supports:
        - Local RMS/amplitude thresholding to filter out silence/static.
        - Groq Speech-to-Text API using whisper-large-v3 model.
        - Filtering of Whisper silence-hallucination loops.
        """
        if not self.api_key:
            print("[WHISPER GROQ] Error: Groq API key is not configured.")
            raise sr.UnknownValueError("API key not configured")

        if not audio_data:
            raise sr.UnknownValueError("No audio data provided")

        try:
            # ── RMS SILENCE FILTER ──────────────────────────────────────────
            # Calculate RMS amplitude of raw frame data to bypass processing silent rooms
            raw_pcm = audio_data.frame_data
            if raw_pcm:
                audio_array = np.frombuffer(raw_pcm, dtype=np.int16)
                if len(audio_array) > 0:
                    rms = np.sqrt(np.mean(audio_array.astype(np.float64)**2))
                    # Threshold of 280 filters out louder ambient static/laptop fan hum
                    if rms < 280:
                        print(f"🤫 [WHISPER GROQ] Audio is too quiet (RMS: {rms:.1f} < 280). Discarding as silence.")
                        raise sr.UnknownValueError("Audio is too quiet/silent")
                    else:
                        print(f"🎙️ [WHISPER GROQ] Audio activity detected (RMS: {rms:.1f}). Sending to Groq STT...")

            # ── CONVERT AUDIO TO WAV IN-MEMORY ──────────────────────────────
            wav_data = audio_data.get_wav_data()
            if not wav_data:
                raise sr.UnknownValueError("Failed to get WAV bytes from audio data")

            # ── CALL GROQ TRANSCRIPTIONS API ────────────────────────────────
            files = {
                "file": ("audio.wav", io.BytesIO(wav_data), "audio/wav")
            }
            data = {
                "model": "whisper-large-v3",
                "language": "en"
            }
            headers = {
                "Authorization": f"Bearer {self.api_key}"
            }

            url = os.getenv("URL_GROQ_STT") or "https://api.groq.com/openai/v1/audio/transcriptions"
            response = requests.post(
                url,
                headers=headers,
                files=files,
                data=data,
                timeout=12
            )

            if response.status_code != 200:
                print(f"⚠️ [WHISPER GROQ API ERROR] Status {response.status_code}: {response.text}")
                raise sr.UnknownValueError(f"Groq API error: {response.status_code}")

            res_json = response.json()
            text = res_json.get("text", "").strip()

            if not text:
                raise sr.UnknownValueError("Transcription resulted in empty text")

            # ── HALLUCINATION FILTER ────────────────────────────────────────
            # Whisper hallucination blocklist for silence/static echos
            clean_text = text.lower().strip().replace(".", "").replace(",", "").replace("?", "").replace("!", "")
            HALLUCINATIONS = {
                "you", "thank you", "thanks for watching", "thank you for watching", "bye", "subtitles by",
                "subscribe", "please subscribe", "thanks for watching!", "thank you!", "subtitles by amaraorg"
            }
            if clean_text in HALLUCINATIONS:
                print(f"🤫 [WHISPER GROQ] Discarded silence hallucination: '{text}'")
                raise sr.UnknownValueError("Silence hallucination detected")

            return text

        except sr.UnknownValueError as uve:
            raise uve
        except Exception as e:
            print(f"⚠️ [WHISPER GROQ ERROR] {e}")
            raise sr.UnknownValueError(f"Transcription failed: {e}")
