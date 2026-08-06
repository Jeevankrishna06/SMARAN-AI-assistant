import queue
import threading
import win32com.client
import pythoncom
import sys

# Configure stdout encoding to handle emojis/unicode on Windows console
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def _get_all_voice_tokens():
    tokens = []
    # Only retrieve Classic SAPI5 voices. Speech_OneCore voices are incompatible 
    # with the classic SAPI5 SpVoice dispatcher and play silently on Windows.
    try:
        speaker = win32com.client.Dispatch("SAPI.SpVoice")
        sapi5_voices = speaker.GetVoices()
        for i in range(sapi5_voices.Count):
            tokens.append(sapi5_voices.Item(i))
    except Exception as e:
        print(f"[VOICE ENGINE WARNING] Could not enumerate SAPI5 voices: {e}")
        
    return tokens

def _find_best_voice(gender, tokens):
    if gender == "female":
        # 1. British English Hazel
        for token in tokens:
            try:
                desc = token.GetDescription().lower()
                if "hazel" in desc:
                    return token
            except Exception:
                pass
        # 2. British English Susan
        for token in tokens:
            try:
                desc = token.GetDescription().lower()
                if "susan" in desc:
                    return token
            except Exception:
                pass
        # 3. Any British Female
        for token in tokens:
            try:
                desc = token.GetDescription().lower()
                if ("gb" in desc or "united kingdom" in desc or "great britain" in desc) and ("female" in desc or "desktop" in desc):
                    return token
            except Exception:
                pass
        # 4. Any Female voice
        for token in tokens:
            try:
                desc = token.GetDescription().lower()
                if "female" in desc or "zira" in desc or "hazel" in desc or "susan" in desc or "heera" in desc or "neerja" in desc or "veena" in desc:
                    return token
            except Exception:
                pass
    else:  # male
        # 1. British English George
        for token in tokens:
            try:
                desc = token.GetDescription().lower()
                if "george" in desc:
                    return token
            except Exception:
                pass
        # 2. Any British Male
        for token in tokens:
            try:
                desc = token.GetDescription().lower()
                if ("gb" in desc or "united kingdom" in desc or "great britain" in desc) and "male" in desc:
                    return token
            except Exception:
                pass
        # 3. Any Male voice
        for token in tokens:
            try:
                desc = token.GetDescription().lower()
                if "male" in desc or "david" in desc or "george" in desc or "ravi" in desc or "karan" in desc or "harsh" in desc:
                    return token
            except Exception:
                pass

    # Absolute fallback
    if tokens:
        return tokens[0]
    return None

class SmaranVoice:
    def __init__(self):
        self.queue = queue.Queue()
        self.current_gender = "male"
        self._start_worker_thread()

    def _start_worker_thread(self):
        self.worker_thread = threading.Thread(target=self._tts_worker, daemon=True)
        self.worker_thread.start()

    def check_voices_status(self):
        """Returns presence of Indian English male/female voices"""
        pythoncom.CoInitialize()
        tokens = []
        try:
            speaker = win32com.client.Dispatch("SAPI.SpVoice")
            sapi5_voices = speaker.GetVoices()
            for i in range(sapi5_voices.Count):
                tokens.append(sapi5_voices.Item(i).GetDescription().lower())
        except Exception:
            pass
            
        try:
            category = win32com.client.Dispatch("SAPI.SpObjectTokenCategory")
            category.SetId(r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech_OneCore\Voices", False)
            onecore_voices = category.EnumerateTokens()
            for i in range(onecore_voices.Count):
                tokens.append(onecore_voices.Item(i).GetDescription().lower())
        except Exception:
            pass
            
        has_indian_male = any("india" in desc and ("male" in desc or "ravi" in desc or "karan" in desc or "harsh" in desc) for desc in tokens)
        has_indian_female = any("india" in desc and ("female" in desc or "heera" in desc or "neerja" in desc or "veena" in desc) for desc in tokens)
        
        return {
            "has_indian_male": has_indian_male,
            "has_indian_female": has_indian_female,
            "total_voices": len(tokens)
        }

    def _tts_worker(self):
        pythoncom.CoInitialize()
        
        speaker = None
        try:
            # Instantiate native Windows speech synthesis engine
            speaker = win32com.client.Dispatch("SAPI.SpVoice")
            speaker.Volume = 100   # Maximum volume
            speaker.Rate = 0       # Normal speaking rate
            
            # Select voice based on current_gender
            try:
                tokens = _get_all_voice_tokens()
                target_voice = _find_best_voice(self.current_gender, tokens)
                if target_voice:
                    speaker.Voice = target_voice
                    print(f"[VOICE ENGINE] Initialized voice: {target_voice.GetDescription()} ({self.current_gender})")
                elif tokens:
                    speaker.Voice = tokens[0]
                    print(f"[VOICE ENGINE] Fallback voice: {tokens[0].GetDescription()}")
                else:
                    print("[VOICE ENGINE WARNING] No voices found at startup!")
            except Exception as e:
                print(f"[VOICE SELECTION WARNING] {e}")
                
        except Exception as e:
            print(f"[TTS INIT ERROR] Failed to initialize native SAPI: {e}")
            speaker = None

        while True:
            try:
                queue_item = self.queue.get()
            except Exception:
                break
            
            # Check for control commands in the queue
            if isinstance(queue_item, tuple) and len(queue_item) == 2 and queue_item[0] == "SET_GENDER":
                gender = queue_item[1]
                if speaker:
                    try:
                        tokens = _get_all_voice_tokens()
                        target_voice = _find_best_voice(gender, tokens)
                        if target_voice:
                            speaker.Voice = target_voice
                            speaker.Volume = 100
                            speaker.Rate = 0
                            print(f"[VOICE ENGINE] Voice gender set to: {gender} ({target_voice.GetDescription()})")
                        elif tokens:
                            speaker.Voice = tokens[0]
                    except Exception as e:
                        print(f"[VOICE ENGINE ERROR] Failed to change voice: {e}")
                self.queue.task_done()
                continue
            
            # Speech item: (text, done_event)
            if isinstance(queue_item, tuple) and len(queue_item) == 2:
                text, done_event = queue_item
            else:
                # Unexpected format — skip it
                self.queue.task_done()
                continue
                
            if speaker and text:
                try:
                    speaker.Speak(text)
                except Exception as e:
                    print(f"[TTS SPEAK ERROR] {e} — attempting SAPI reinit...")
                    try:
                        speaker = win32com.client.Dispatch("SAPI.SpVoice")
                        speaker.Volume = 100
                        speaker.Rate = 0
                        tokens = _get_all_voice_tokens()
                        target_voice = _find_best_voice(self.current_gender, tokens)
                        if target_voice:
                            speaker.Voice = target_voice
                        speaker.Speak(text)
                    except Exception as e2:
                        print(f"[TTS REINIT FAILED] {e2}")
            elif not speaker:
                print(f"[TTS ERROR] Native SpVoice not initialized. Skipped: '{text}'")
            
            done_event.set()
            self.queue.task_done()

    def set_voice_gender(self, gender):
        """Sets the active SAPI voice gender ('male' or 'female')"""
        self.current_gender = gender
        self.queue.put(("SET_GENDER", gender))

    def speak(self, text):
        """Speaks strings aloud safely using the dedicated TTS worker thread"""
        if not text:
            return

        # SAPI5 UNICODE SANITIZATION
        # SAPI5 on Windows hangs silently on curly quotes, em-dashes, and other
        # Unicode punctuation that Groq commonly returns. Replace before queuing.
        text = text.replace('\u2019', "'")   # Right single quote (You're -> You're)
        text = text.replace('\u2018', "'")   # Left single quote
        text = text.replace('\u201c', '"')   # Left double quote
        text = text.replace('\u201d', '"')   # Right double quote
        text = text.replace('\u2013', '-')   # En dash
        text = text.replace('\u2014', '-')   # Em dash
        text = text.replace('\u2026', '...')  # Ellipsis
        text = text.replace('\u00a0', ' ')   # Non-breaking space
        text = text.replace('\u2022', '-')   # Bullet point
        # Strip any remaining non-ASCII that SAPI5 cannot handle
        text = text.encode('ascii', errors='ignore').decode('ascii')

        # Restart worker thread if it has died
        if not self.worker_thread.is_alive():
            print("[VOICE ENGINE] Worker thread died - restarting...")
            self._start_worker_thread()

        # Block the calling thread until speaking finishes.
        # Estimate speaking time dynamically to prevent false timeouts on long texts:
        # SAPI5 speaks at roughly 130-150 words per minute (approx. 2 words/sec).
        # We calculate a dynamic timeout: (words / 2) + 30 seconds buffer.
        word_count = len(text.split())
        dynamic_timeout = max(45.0, (word_count / 2.0) + 30.0)

        done_event = threading.Event()
        self.queue.put((text, done_event))
        finished = done_event.wait(timeout=dynamic_timeout)
        if not finished:
            print(f"[TTS TIMEOUT] Speech timed out after {dynamic_timeout:.1f}s for: '{text[:50]}...'")
            # Restart worker so TTS doesn't stay dead after a timeout
            print("[VOICE ENGINE] Restarting TTS worker after timeout...")
            self._start_worker_thread()