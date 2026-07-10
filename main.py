import os
import sys
import re
import threading
import time
import speech_recognition as sr
from os_controller import OSController
from voice_engine import SmaranVoice
from smaran_brain import SmaranBrain
from gui import SmaranGUI, PandaStateManager
from weather_agent import WeatherAgent
from dictionary_agent import DictionaryAgent
from wikipedia_agent import WikipediaAgent
from news_agent import NewsAgent
from gemini_agent import GeminiAgent
from whisper_transcriber import WhisperTranscriber
import clap_detector
from dotenv import load_dotenv

# Path to the .env file is actually inside a folder named .env (c:\Users\HP\OneDrive\Desktop\Smaran-AI Assistant(AUTOMATION AGENT)\.env\.env)
dotenv_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
dotenv_file = os.path.join(dotenv_dir, ".env")
if os.path.exists(dotenv_file):
    load_dotenv(dotenv_file)
else:
    # Try normal load_dotenv fallback
    load_dotenv()
# Configure stdout encoding to handle emojis on Windows console
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

class DualStream:
    def __init__(self, original_stream, log_file_path):
        self.original_stream = original_stream
        self.log_file_path = log_file_path

    def write(self, message):
        # Safely print to console, converting unsupported characters (e.g. emojis) to clean text/backslashes
        try:
            self.original_stream.write(message)
        except UnicodeEncodeError:
            # Fallback for standard console stdout/stderr which may be using cp1252 or other non-utf8 encodings
            safe_msg = message.encode(self.original_stream.encoding or 'ascii', errors='backslashreplace').decode(self.original_stream.encoding or 'ascii')
            self.original_stream.write(safe_msg)
        self.original_stream.flush()
        if message.strip():
            try:
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                with open(self.log_file_path, "a", encoding="utf-8") as f:
                    f.write(f"[{timestamp}] {message.strip()}\n")
            except Exception:
                pass

    def flush(self):
        self.original_stream.flush()

    def __getattr__(self, attr):
        return getattr(self.original_stream, attr)

# Redirect stdout and stderr to both console and system log file
log_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "smaran_system.log")
sys.stdout = DualStream(sys.stdout, log_file_path)
sys.stderr = DualStream(sys.stderr, log_file_path)

class SmaranCore:
    def __init__(self):
        print("\n⚡ ACTIVATING SMARAN! ⚡\n")
        self.brain = SmaranBrain() 
        self.os_control = OSController()
        self.voice = SmaranVoice()
        self.weather_agent = WeatherAgent()
        self.dictionary_agent = DictionaryAgent()
        self.wikipedia_agent = WikipediaAgent()
        self.news_agent = NewsAgent()
        self.gemini_agent = GeminiAgent()
        self.router_debug = True # Set to True for debugging router logic
        self.is_speaking = False       # True while TTS is active — suppresses mic to prevent echo loop
        self.speech_finished_at = 0.0   # Timestamp when last TTS finished — used for post-speech cooldown
        self.intelligence_mode = False  # When True, ALL prompts route to Groq with history
        self.intel_history = []         # Conversation history for Intelligence Mode (max 20 entries = 10 exchanges)
        self.intel_context = {"last_entity": None, "last_agent": None} # Conversational context memory
        self.quiet_mode = False         # When True, all mic listening is suspended (UI and text stay active)
        self.recognizer = sr.Recognizer()
        self.transcriber = WhisperTranscriber()
        self.recognizer.energy_threshold = 200   # High enough to ignore laptop fan/ambient noise, low enough to catch speech
        self.recognizer.dynamic_energy_threshold = False  # Keep threshold fixed — dynamic mode lets fan noise raise it and deafen the mic
        self.recognizer.pause_threshold = 2.0    # Wait 2s of silence before ending a phrase — gives user time to pause between words
        self.recognizer.phrase_threshold = 0.02   # Extremely low so short impulsive claps are not discarded by the engine
        self.recognizer.non_speaking_duration = 0.08  # Short pre-phrase buffer
        try:
            self.mic = sr.Microphone()
        except Exception as e:
            print(f"microphone seems unavailable: {e}")
            self.mic = None
            
        self.gui = None #because GUI is launched on main thread, we initialize it here but it will be set in launch_visual_console()
        self.wake_triggered = False #what happens when it is set to true is that the passive radar will stop and the active listening will start
        self.stop_listening_fn = None
        self._mic_lock = threading.Lock()  # Prevents two listeners from opening the mic simultaneously
        
        # Spawn GUI and start running on the main thread immediately!
        self.launch_visual_console()

    def stop_passive_radar_cleanly(self):
        """Stops the passive background wake listener and waits for mic release""" #it performs a clean shutdown of the passive radar listener, ensuring that the microphone is released and any background threads are properly terminated.
        fn = self.stop_listening_fn 
        if fn is not None:
            self.stop_listening_fn = None
            print("🔇 [RADAR DEACTIVATED] Stopping passive radar listener...", flush=True)
            try:
                # Put a chunk of silence to unblock listener thread from queue.get()
                if hasattr(self, 'radar_mic') and self.radar_mic:
                    self.radar_mic.audio_queue.put(b'\x00' * (self.radar_mic.CHUNK * 2)) #what it does is that it puts a chunk of silence into the audio queue to unblock the listener thread from waiting indefinitely on audio input. This allows the background listener to exit cleanly.
                fn(wait_for_stop=True)
                print("✅ [RADAR DEACTIVATED] Passive radar listener fully stopped.", flush=True) # what it does is that it prints a confirmation message indicating that the passive radar listener has been successfully stopped and the microphone is now released for other uses.
            except Exception as e:
                print(f"[RADAR STOP WARNING] {e}", flush=True)

    def stable_passive_radar(self):
        """STATE 1: Listens in background continuously until wake word hits"""
        if not self.mic:
            print("❌ microphone is  unavailable. Exiting passive radar.")
            return

        # Wait for Whisper model to finish loading before calibrating/listening
        while self.transcriber.loading or self.transcriber.model is None:
            print("⏳ [RADAR] Waiting for Whisper model to finish loading...")
            time.sleep(1.0)

        # Update status to Standby once loaded
        if self.gui:
            self.state_manager.set_state("idle", "Standby")

        print("🎧 [RADAR CALIBRATION] for checking any ambient sounds from the environment.") #this prints because 
        try:
            # Use a fresh mic instance for calibration only — separate from the one used for listening
            calib_mic = sr.Microphone()
            with calib_mic as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1.25)
        except Exception as e:
            print(f"⚠️ RADAR Error: {e}")

        # Let the OS fully release the audio device from calibration before entering radar_mic
        time.sleep(1.25)

        print(" Smaran is waiting for your order boss/mam!")
        if self.gui:
            self.state_manager.set_state("idle", "Say 'Wake up'")

        def on_clap():
            print("\n[WAKE]")
            print("Clap detected.")
            print("Smaran awakened.")
            self.wake_triggered = True
            
            def stop_and_wake():
                self.stop_passive_radar_cleanly()
                # Force trigger active listening on main thread
                if self.gui:
                    self.gui.root.after(0, self.initialize_assistant)
                else:
                    threading.Thread(target=self.initialize_assistant, daemon=True).start()

            threading.Thread(target=stop_and_wake, daemon=True).start()

        try:
            radar_mic = clap_detector.BufferedMicSource(
                on_clap_callback=on_clap,
                check_active_callback=lambda: getattr(self, 'wake_triggered', False),
                device_index=self.mic.device_index if self.mic else None
            )
            self.radar_mic = radar_mic
            # Revert to standard phrase threshold since claps are handled by our proxy
            self.recognizer.phrase_threshold = 0.3
            self.stop_listening_fn = self.recognizer.listen_in_background(
                radar_mic,
                self.wake_word_callback,
                phrase_time_limit=4
            )
            print("🎤 [RADAR ACTIVE] Background acoustic scanning array active.")
            
        except Exception as e:
            print(f"⚠️ [RADAR ERROR] Could not start background wake listener: {e}") 
            if self.gui:
                self.state_manager.set_state("idle", "Text entry ready")  # Fallback to text entry if mic fails

        # Keep thread alive until wake word is triggered
        while not self.wake_triggered:
            time.sleep(0.5)



    def wake_word_callback(self, recognizer, audio):
        """Callback for background wake word listener"""
        if self.wake_triggered:
            return
        # Process transcription asynchronously in a separate thread
        threading.Thread(target=self._process_wake_audio, args=(audio,), daemon=True).start()

    def _process_wake_audio(self, audio):
        if self.wake_triggered:
            return
            
        if self.gui:
            self.state_manager.set_state("thinking", "Verifying wake word...")
            
        try:
            spoken_text = self.transcriber.transcribe(audio, mode="fast").lower()
            print(f"👂 [RADAR HEARD] Detected audio: '{spoken_text}'")
            
            # Flexible phonetic wake-word matching to handle model/mic variations
            name_matches = ["smaran", "samaran", "sumran", "smoran", "simran", "some run","smurren","smurrel","smarren", "somrun"]
            is_wake_name = any(w in spoken_text for w in name_matches)
            
            # Check for phonetic name matches with "hey/hi" prefix (e.g. "hey smart", "hey summer")
            prefix_matches = ["smart", "summer", "summary", "someone", "marine", "maran"]
            has_prefix = any(p in spoken_text for p in ["hey ", "hi ", "ok ", "okay ","hello "])
            is_prefixed_wake = has_prefix and any(w in spoken_text for w in prefix_matches)
            
            # Check for wake up phrases
            is_wake_up = any(w in spoken_text for w in ["wake up", "wakeup", "way cup", "lake up", "make up", "weicup"])
            
            if is_wake_name or is_prefixed_wake or is_wake_up:
                print("⚡ [WAKE INITIALIZED] Wake word detected!")
                self.wake_triggered = True
                
                # Stop the background wake listener cleanly and wait for release
                self.stop_passive_radar_cleanly()
                    
                # Play greeting and start active directive listening
                self.initialize_assistant()
            else:
                if self.gui and not self.wake_triggered:
                    self.state_manager.set_state("idle", "Say 'Wake up'")
        except Exception as e:
            print(f"⚠️ [RADAR TRANSCRIBE WARNING] {e}")
            if self.gui and not self.wake_triggered:
                self.state_manager.set_state("idle", "Say 'Wake up'")

    def launch_visual_console(self):
        """Assembles the UI window on the main thread and starts background loops"""
        self.gui = SmaranGUI(on_send_callback=self.pipeline, on_voice_change_callback=self.handle_voice_change)
        self.state_manager = PandaStateManager(self.gui) # Centralized state manager 
        
        # Apply the default gender from GUI to SAPI on startup
        self.handle_voice_change()
        
        # Set initial GUI state to idle showing "Initializing..."
        self.state_manager.set_state("idle", "Initializing...")
        
        # Start the passive background wake loop in a thread
        threading.Thread(target=self.stable_passive_radar, daemon=True).start()
        
        self.gui.run()

    def initialize_assistant(self):
        """Plays greeting and arms microphone sequentially"""
        if self.gui:
            self.state_manager.set_state("idle", "Activating...")

        # Prioritize a quick, highly recognizable wake-up audio and store the resolved path
        self.wake_wav_path = r"C:\Windows\Media\Windows Unlock.wav"
        if not os.path.exists(self.wake_wav_path):
            self.wake_wav_path = r"C:\Windows\Media\Windows Logon.wav"
        if not os.path.exists(self.wake_wav_path):
            self.wake_wav_path = r"C:\Windows\Media\Windows Background.wav"
        if not os.path.exists(self.wake_wav_path):
            self.wake_wav_path = r"C:\Windows\Media\chimes.wav"

        # Play the introductory audio chime synchronously here  
        try:
            import winsound
            winsound.PlaySound(self.wake_wav_path, winsound.SND_FILENAME)
        except Exception as e:
            print(f"[WAKE AUDIO ERROR] {e}")
            
        greeting = "I have been activated, boss. ready to serve you."
        self.speak(greeting, "Speaking greeting...")
        self.start_active_listening()

    def speak(self, text, task_desc=None): 
        """Helper to speak text — mutes mic during TTS to prevent audio feedback echo loops"""
        text = re.sub(r'\bsir\b', 'boss', text, flags=re.IGNORECASE)
        text = re.sub(r'\bmam\b', 'boss', text, flags=re.IGNORECASE)
        text = re.sub(r'\bmadam\b', 'boss', text, flags=re.IGNORECASE) 
        
        if self.gui:
            self.state_manager.set_state("speaking", task_desc)
        self.is_speaking = True      # Suppress mic — prevents TTS audio being picked up as input
        try:
            self.voice.speak(text)   # Blocking call — mic stays suppressed for full duration
        finally:
            self.is_speaking = False
            self.speech_finished_at = time.time()  # Mark when TTS ended — cooldown window starts now

    # ── INTELLIGENCE MODE ─────────────────────────────────────────────────────

    def _fuzzy_matches(self, spoken: str, target: str, threshold: float = 0.82) -> bool: 
        """
        Returns True if spoken text fuzzy-matches the target phrase.
        Uses word-sequence matching + difflib ratio.
        Word-sequence check prevents 'activate intelligence' matching
        inside 'deactivate intelligence'.
        """
        from difflib import SequenceMatcher
        spoken = spoken.lower().strip()
        target = target.lower().strip()
        # Full string match
        if spoken == target:
            return True
        # Word-sequence match: all target words appear consecutively in spoken
        sw = spoken.split()
        tw = target.split()
        for i in range(len(sw) - len(tw) + 1): #
            if sw[i:i + len(tw)] == tw:
                return True
        # Fuzzy ratio fallback for Whisper transcription errors
        return SequenceMatcher(None, spoken, target).ratio() >= threshold

    def _check_intel_command(self, text: str):
        """
        Checks if the spoken text is an Intelligence Mode activation or deactivation command.
        Returns: 'activate' | 'deactivate' | None

        Uses first-word prefix routing to prevent cross-category false-positives:
        'deactivate intelligence' first word is 'deactivate' -> only checks DEACTIVATE.
        'activate intelligence' first word is 'activate' -> only checks ACTIVATE.
        """
        ACTIVATE_PREFIXES   = {"initiate", "activate", "enter"}
        DEACTIVATE_PREFIXES = {"lock", "deactivate", "exit","stop","quit"}

        ACTIVATE_PHRASES = [
            "initiate intelligence",
            "activate intelligence",
            "activate intelligence mode",
            "enter intelligence mode",
            "initiate intelligent",
            "activate intelligent",
            "enter intelligent",
            "enter intelligence",
            "initiate intelligence mode",
        ]
        DEACTIVATE_PHRASES = [
            "lock intelligence",
            "deactivate intelligence",
            "exit intelligence mode",
            "exit intelligent",
            "stop intelligence",
            "quit intelligence",
            "stop intelligent",
            "stop intelligence mode",
            "quit intelligence mode",
            "quit intelligent",
            "lock intelligent",
            "lock intelligence mode",
            "deactivate intelligence mode",
            "deactivate intelligent",
            "exit intelligence",
        ]

        first_word = text.split()[0] if text.split() else ""

        if first_word in ACTIVATE_PREFIXES:
            for phrase in ACTIVATE_PHRASES:
                if self._fuzzy_matches(text, phrase):
                    return "activate"
        elif first_word in DEACTIVATE_PREFIXES:
            for phrase in DEACTIVATE_PHRASES:
                if self._fuzzy_matches(text, phrase):
                    return "deactivate"
        else:
            # Unknown first word — try deactivate first, then activate
            for phrase in DEACTIVATE_PHRASES:
                if self._fuzzy_matches(text, phrase):
                    return "deactivate"
            for phrase in ACTIVATE_PHRASES:
                if self._fuzzy_matches(text, phrase):
                    return "activate"
        return None

    def _clean_extracted_entity(self, text: str) -> str:
        """
        Cleans common filler words, question prefixes, prepositions, and articles
        from the beginning and end of an extracted entity (topic, city, word).
        """
        if not text:
            return ""
        
        # Lowercase and strip whitespace
        text = text.lower().strip()
        
        # Word-by-word cleanup from the beginning/end
        fillers = {
            "give", "me", "tell", "show", "what", "is", "was", "are", "were", "does", "do",
            "the", "a", "an", "on", "about", "from", "of", "to", "for", "in", "at", "with",
            "search", "find", "get", "look", "up", "latest", "recent", "current", "news",
            "wikipedia", "wiki", "definition", "meaning", "define", "pronounce", "pronunciation",
            "word", "term", "summary", "summarize", "forecast", "weather", "info", "information",
            "headline", "headlines", "detail", "details", "please", "pls", "can", "you", "could", "would",
            "and", "or", "but", "our", "my", "your", "his", "her", "their", "its", "us", "them", "here", "there",
            "it", "this", "that", "some", "any", "all", "out", "when", "time"
        }
        
        # Loop to strip fillers from start and end, leaving at least one word
        words = text.split()
        while len(words) > 1 and words[0] in fillers:
            words.pop(0)
        while len(words) > 1 and words[-1] in fillers:
            words.pop()
            
        cleaned = " ".join(words).strip() #cleans up any extra spaces after popping fillers
        # Remove any trailing question marks or punctuation
        cleaned = re.sub(r'^[^\w]+|[^\w]+$', '', cleaned)
        return cleaned.strip()

    def _analyze_intent(self, user_input: str) -> tuple[str, float]:
        """
        Analyzes the user query to classify it into one of:
        Weather, Dictionary, Research, News, Reasoning, System Command, Mode Activation, Unknown.
        Returns (intent_label, confidence_score).
        """
        text = user_input.lower().strip()
        text_words = set(text.split())
        
        # 1. Mode Activation Check
        mode_triggers = {
            "study mode", "developer mode", "fun mode", "deep mode", "dev mode",
            "activate vision", "start vision", "vision mode", "enable vision",
            "lock vision", "disable vision", "stop vision", "close vision"
        }
        if any(trigger in text for trigger in mode_triggers):
            intent, confidence = "Mode Activation", 1.0
            print(f"[INTEL]\nIntent: {intent}\nConfidence: {confidence}\n")
            return intent, confidence

        # 2. System Command Check
        sys_triggers = {
            "volume", "mute", "shutdown", "stop", "exit", "bye", "goodbye", "sleep", "goodnight",
            "timer", "clock", "countdown", "calculate", "compute", "solve", "type", "write",
            "notepad", "calculator", "calc", "cmd", "explorer", "task manager"
        }
        is_open_cmd = (text.startswith("open ") or text.startswith("launch "))
        if is_open_cmd or any(t in text_words for t in sys_triggers) or "set timer" in text or "countdown" in text:
            if not any(w in text for w in ["wikipedia", "wiki", "weather", "news", "define", "definition", "meaning"]):
                intent, confidence = "System Command", 0.9
                print(f"[INTEL]\nIntent: {intent}\nConfidence: {confidence}\n")
                return intent, confidence

        # 3. Keyword Scoring for other categories
        scores = {
            "Weather": 0,
            "Dictionary": 0,
            "Research": 0,
            "News": 0,
            "Reasoning": 0
        }
        
        keywords = {
            "Weather": ["weather", "forecast", "temperature", "temp", "climate", "rain", "humidity", "sunrise", "sunset", "wind"],
            "Dictionary": ["define", "definition", "meaning", "mean", "pronounce", "pronunciation", "part of speech"],
            "Research": ["wikipedia", "wiki", "research", "who is", "who was", "history of", "tell me about", "information about"],
            "News": ["news", "headlines", "headline", "current events", "what's happening in", "what happened in", "latest news"],
            "Reasoning": ["explain", "compare", "versus", " vs ", "summarize", "summary", "analyze", "analysis", "why is", "how do", "should i", "which is better"]
        }
        
        for category, kw_list in keywords.items():
            for kw in kw_list:
                if " " in kw:
                    if kw in text:
                        scores[category] += 2
                elif re.search(r'\b' + re.escape(kw) + r'\b', text):
                    scores[category] += 1
                    
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        highest_cat, highest_score = sorted_scores[0]
        second_highest_score = sorted_scores[1][1] if len(sorted_scores) > 1 else 0
        
        if highest_score > 0:
            confidence = (highest_score - second_highest_score) / highest_score if highest_score > 0 else 0.0
            confidence = min(1.0, max(0.2, confidence * (highest_score / (highest_score + 1))))
            intent, confidence = highest_cat, round(confidence, 2)
            print(f"[INTEL]\nIntent: {intent}\nConfidence: {confidence}\n")
            return intent, confidence
            
        intent, confidence = "Unknown", 0.0
        print(f"[INTEL]\nIntent: {intent}\nConfidence: {confidence}")
        return intent, confidence

    def _resolve_context(self, user_input: str, intent: str) -> tuple[str, str]:
        """
        Resolves pronouns in the user_input using self.intel_context if available.
        Returns (resolved_query, resolved_agent).
        """
        last_entity = self.intel_context.get("last_entity")
        last_agent = self.intel_context.get("last_agent")
        
        if not last_entity:
            return user_input, None
            
        # Pronouns to replace
        pronouns = ["he", "she", "it", "they", "him", "his", "her", "them", "their"]
        
        # Check if any pronoun is in the query (as a word)
        words = re.findall(r'\b\w+\b', user_input.lower())
        has_pronoun = any(p in words for p in pronouns)
        
        if has_pronoun:
            # Replace pronouns with last_entity
            resolved_query = user_input
            for p in pronouns:
                resolved_query = re.sub(rf'\b{p}\b', last_entity, resolved_query, flags=re.IGNORECASE)
            print(f"[INTEL] Context resolved: Pronoun replaced with '{last_entity}' -> '{resolved_query}'")
            return resolved_query, last_agent
            
        return user_input, None

    def _extract_entity(self, query: str, intent: str) -> str:
        """
        Centrally extracts the clean entity (topic, city, word) based on intent.
        """
        if not intent:
            return self._clean_extracted_entity(query)
            
        intent_lower = intent.lower()
        if intent_lower == "weather":
            city = query.lower()
            weather_removals = [
                # Questions/Commands
                "what is the weather in", "what's the weather in", "weather summary in", "weather summary for",
                "will it rain today in", "will it rain in", "is it raining in",
                "give me the weather summary of", "give me weather summary of", "give me weather summary in",
                "what time is the", "what time is", "when is the", "when is",
                # Rain/Precipitation metrics
                "rain probability today in", "rain probability in", "rain probability for", "rain probability of",
                "precipitation probability today in", "precipitation probability in", "precipitation probability for", "precipitation probability of",
                "rain chances today in", "rain chances in", "rain chances for", "rain chances of",
                "chance of rain today in", "chance of rain in", "chance of rain for", "chance of rain of",
                "rain today in", "rain in", "rain for", "rain",
                # Max temperature metrics
                "maximum temperature today in", "maximum temperature in", "maximum temperature of", "maximum temperature for",
                "max temperature today in", "max temperature in", "max temperature of", "max temperature for",
                "maximum temp today in", "maximum temp in", "maximum temp of", "maximum temp for",
                "max temp today in", "max temp in", "max temp of", "max temp for",
                # Min temperature metrics
                "minimum temperature today in", "minimum temperature in", "minimum temperature of", "minimum temperature for",
                "min temperature today in", "min temperature in", "min temperature of", "min temperature for",
                "minimum temp today in", "minimum temp in", "minimum temp of", "minimum temp for",
                "min temp today in", "min temp in", "min temp of", "min temp for",
                # General temperature metrics
                "temperature in", "temperature for", "temperature of", "temperature",
                "temp in", "temp for", "temp of", "temp",
                # Wind metrics
                "wind speed in", "wind speed for", "wind speed of", "wind speed",
                "wind in", "wind for", "wind of",
                # Sunrise/Sunset metrics
                "sunrise in", "sunrise for", "sunrise",
                "sunset in", "sunset for", "sunset",
                # Other indicators
                "humidity in", "humidity for", "humidity of", "humidity",
                "climate in", "climate for", "climate of", "climate",
                "forecast for", "forecast in", "forecast",
                "weather in", "weather for", "weather of", "weather at", "weather",
                "today", "tomorrow", "now", "what is the", "what's the", "tell me about", "get me the", "give me", "show me"
            ]
            weather_removals.sort(key=len, reverse=True)
            for w in weather_removals:
                city = city.replace(w, "")
            return self._clean_extracted_entity(city)
            
        elif intent_lower == "dictionary":
            cleaned_text = query.lower().strip()
            patterns = [
                r"tell me the meaning of\s+(.+)",
                r"meaning of the\s+(.+)",
                r"definition of the\s+(.+)",
                r"pronunciation of the\s+(.+)",
                r"part of speech of the\s+(.+)",
                r"what does\s+(.+)\s+mean",
                r"definition of\s+(.+)",
                r"meaning of\s+(.+)",
                r"pronunciation of\s+(.+)",
                r"part of speech of\s+(.+)",
                r"tell me the\s+(.+)",
                r"what is the\s+(.+)",
                r"what's the\s+(.+)",
                r"what does\s+(.+)",
                r"what is\s+(.+)",
                r"define\s+(.+)",
                r"meaning\s+(.+)",
                r"definition\s+(.+)",
                r"pronounce\s+(.+)",
                r"pronunciation\s+(.+)",
                r"mean\s+(.+)"
            ]
            word = None
            for pattern in patterns:
                match = re.search(pattern, cleaned_text)
                if match:
                    word = match.group(1).strip()
                    break
            if not word:
                word = cleaned_text
            return self._clean_extracted_entity(word)
            
        elif intent_lower == "news":
            cleaned_text = query.lower().strip()
            patterns = [
                r"give me the latest news on\s+(.+)",
                r"give me the latest news about\s+(.+)",
                r"give me the latest headlines on\s+(.+)",
                r"give me the latest headlines about\s+(.+)",
                r"give me latest news on\s+(.+)",
                r"give me latest news about\s+(.+)",
                r"give me news on\s+(.+)",
                r"give me news about\s+(.+)",
                r"news about\s+(.+)",
                r"news on\s+(.+)",
                r"news of\s+(.+)",
                r"headlines about\s+(.+)",
                r"headlines on\s+(.+)",
                r"headlines of\s+(.+)",
                r"what's happening in\s+(.+)",
                r"what's going on in\s+(.+)",
                r"what is happening in\s+(.+)",
                r"what is going on in\s+(.+)",
                r"what happened in\s+(.+)",
                r"give me the latest\s+(.+)",
                r"give me the\s+(.+)",
                r"give me\s+(.+)",
                r"headlines\s+(.+)",
                r"headline\s+(.+)",
                r"latest\s+(.+)",
                r"show me\s+(.+)",
                r"tell me\s+(.+)"
            ]
            topic = None
            for pattern in patterns:
                match = re.search(pattern, cleaned_text)
                if match:
                    topic = match.group(1).strip()
                    break
            if not topic:
                topic = cleaned_text
            return self._clean_extracted_entity(topic)
            
        elif intent_lower in ("research", "wikipedia"):
            topic = query.lower()
            wiki_removals = [
                "what is the", "what is", "what's the","who is",
                "search wikipedia for", "wikipedia for", "wikipedia of",
                "search wiki for", "wiki for", "wiki of",
                "wikipedia", "wiki", "on wiki", "on wikipedia",
                "research for", "research on", "research",
                "tell me about", "look up", "search for", "get me","give me information about", "give me info about"
            ]
            wiki_removals.sort(key=len, reverse=True)
            for w in wiki_removals:
                topic = topic.replace(w, "")
            return self._clean_extracted_entity(topic)
            
        elif intent_lower == "reasoning":
            text = query.lower().strip()
            if "explain " in text:
                topic = text.split("explain ")[-1].strip().rstrip('?.!')
                return self._clean_extracted_entity(topic)
            if "summarize " in text:
                target_text = text.split("summarize ")[-1].strip()
                return self._clean_extracted_entity(target_text)
            return self._clean_extracted_entity(query)
            
        return self._clean_extracted_entity(query)

    def _validate_response(self, response: str) -> bool:
        """
        Validates response string for empty/short/error patterns.
        """
        if not response:
            return False
        response_clean = response.strip().lower()
        if len(response_clean) < 5:
            return False
        
        # Error substrings
        error_patterns = [
            "couldn't retrieve",
            "could not retrieve",
            "error:",
            "failed to",
            "api error",
            "internal server error",
            "rate limit",
            "quota exceeded",
            "resource_exhausted",
            "429 resource exhausted",
            "temporarily unavailable",
            "sorry boss, i couldn't",
            "sorry, i couldn't",
        ]
        if any(pat in response_clean for pat in error_patterns):
            return False
            
        return True

    def _make_voice_friendly(self, text: str) -> str:
        """
        Formats text for voice output: removes markdown syntax,
        bracketed citations, and returns a clean spoken format.
        """
        if not text:
            return ""
        text = text.replace("**", "").replace("*", "")
        text = text.replace("`", "")
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
        text = re.sub(r'\[\d+\]', '', text)
        text = re.sub(r'\[citation\]', '', text)
        text = re.sub(r'<[^>]*>', '', text)
        text = " ".join(text.split())
        
        sentences = re.split(r'(?<=[.!?])\s+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        if len(sentences) > 6:
            text = " ".join(sentences[:6])
            
        return text


    def _preprocess_router_query(self, user_input: str) -> str: #this is the main preprocessing function for router scoring and agent selection. It normalizes the query for keyword matching while preserving the original user input for Gemini classification and final execution.
        """Normalizes a query for local scoring while preserving the original elsewhere."""
        text = user_input.lower().strip()
        text = re.sub(r'[^\w\s]', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()

        filler_patterns = [
            r'\bcan you please\b', r'\bcould you please\b', r'\bplease\b',
            r'\bcan you\b', r'\bcould you\b', r'\bwould you\b',
            r'\bi want to know\b', r'\bi need to know\b',
        ]
        for pattern in filler_patterns:
            text = re.sub(pattern, ' ', text)
        return re.sub(r'\s+', ' ', text).strip()

    def _score_intelligence_agents(self, normalized_query: str) -> dict: #performs local keyword scoring for each specialized agent to inform routing decisions. This is a lightweight, interpretable heuristic layer that runs before any LLM calls to Gemini or Groq
        """Scores each specialized intelligence agent using local weighted keywords."""
        phrase_weights = {
            "weather": {
                "weather": 3, "forecast": 3, "temperature": 2, "climate": 2,
                "rain": 2, "humidity": 2, "sunrise": 2, "sunset": 2, "wind": 2, "weather summary": 3,
            },
            "dictionary": {
                "define": 3, "definition": 3, "meaning": 3, "give me the meaning of": 3,
                "mean": 2, "dictionary": 2, "pronounce": 2, "pronunciation": 2,
            },
            "wikipedia": {
                "research": 3, "tell me about": 3, "wikipedia": 3, "wiki": 2,
                "who is": 2, "what is": 2, "history of": 2, "information about": 2,
                "open wikipedia": 3, "search wikipedia": 3,
            },
            "news": {
                "news": 3, "latest news": 3, "headlines": 3, "headline": 2,
                "latest": 1, "current events": 2, "geopolitics": 1, "sports": 1, "sport": 1,
                "breaking": 1, "update": 1, "updates": 1, "technology": 1, "business": 1,
                "economy": 1, "finance": 1, "health": 1, "science": 1,
            },
            "reasoning": {
                "gemini": 3, "explain": 3, "compare": 3, "summarize": 3,
                "predict": 2, "analyze": 2, "versus": 2, " vs ": 2, "should i": 2, "which is better": 2,
                "stats": 1, "statistics": 1, "data": 1,
            },
        }

        padded_query = f" {normalized_query} " #performs both exact phrase matching and individual keyword matching with word boundary checks.
        scores = {agent: 0 for agent in phrase_weights}
        for agent, weights in phrase_weights.items(): 
            for phrase, weight in weights.items():
                if " " in phrase.strip():
                    if phrase in padded_query:
                        scores[agent] += weight
                elif re.search(rf'\b{re.escape(phrase)}\b', normalized_query):
                    scores[agent] += weight
        return scores

    def _select_agent_by_confidence(self, scores: dict, threshold: int = 1):
        sorted_scores = sorted(scores.items(), key=lambda item: item[1], reverse=True) 
        winner, highest_score = sorted_scores[0]
        second_highest_score = sorted_scores[1][1] if len(sorted_scores) > 1 else 0
        confidence_gap = highest_score - second_highest_score

        if highest_score == 0 or highest_score == second_highest_score or confidence_gap < threshold:
            return None, highest_score, second_highest_score, confidence_gap
        return winner, highest_score, second_highest_score, confidence_gap

    def _classify_with_gemini(self, user_input: str) -> str:
        """
        Uses Gemini only as a classifier for ambiguous router decisions.
        Returns one of: weather, dictionary, wikipedia, news, reasoning.
        """
        prompt = (
            "Classify this user query for Smaran's router. Return exactly one label only: "
            "weather, dictionary, wikipedia, news, reasoning. Do not answer the query. "
            "No explanation. No punctuation. Query: "
            f"{user_input.strip()}"
        )
        try:
            if hasattr(self.gemini_agent, "classify_route"):
                label = self.gemini_agent.classify_route(prompt).lower().strip()
            else:
                label = self.gemini_agent._call(prompt, retries=1).lower().strip()
        except Exception as exc:
            print(f"[ROUTER] Gemini classifier failed: {exc}")
            return "reasoning"

        label = re.sub(r'[^a-z]', '', label)
        if label in {"weather", "dictionary", "wikipedia", "news", "reasoning"}:
            return label
        return "reasoning"

    def _execute_weather_agent(self, text: str, extracted_entity: str = None) -> str:
        city = extracted_entity if extracted_entity else text
        if not city:
            city = "Bengaluru"

        if "sunrise" in text:
            return self.weather_agent.get_sunrise(city)
        if "sunset" in text:
            return self.weather_agent.get_sunset(city)
        if "wind" in text:
            return self.weather_agent.get_wind_speed(city)
        if "max" in text or "maximum" in text:
            return self.weather_agent.get_max_temperature(city)
        if "min" in text or "minimum" in text:
            return self.weather_agent.get_min_temperature(city)
        if "temp" in text or "temperature" in text:
            return self.weather_agent.get_temperature(city)
        if "rain" in text or "precipitation" in text or "chance" in text or "probability" in text:
            return self.weather_agent.get_rain_probability(city)
        return self.weather_agent.get_weather_summary(city)

    def _execute_dictionary_agent(self, text: str, extracted_entity: str = None) -> str:
        word = extracted_entity if extracted_entity else text
        if not word:
            return "Please specify the word you want me to look up."
        if "pronounce" in text or "pronunciation" in text:
            return self.dictionary_agent.get_pronunciation(word)
        if "part of speech" in text:
            return self.dictionary_agent.get_part_of_speech(word)
        return self.dictionary_agent.get_dictionary_summary(word)

    def _execute_news_agent(self, text: str, extracted_entity: str = None) -> str:
        topic = extracted_entity if extracted_entity else text
        if topic:
            if "latest" in text:
                return self.news_agent.get_latest_news(topic)
            return self.news_agent.search_news(topic)
        return self.news_agent.get_top_news()

    def _execute_wikipedia_agent(self, text: str, extracted_entity: str = None) -> str:
        topic = extracted_entity if extracted_entity else text
        if not topic:
            return "Please specify the topic you want to look up on Wikipedia."
        if "research" in text or "long" in text:
            return self.wikipedia_agent.get_research_summary(topic)
        if "short" in text or "concise" in text:
            return self.wikipedia_agent.get_short_summary(topic)
        return self.wikipedia_agent.get_summary(topic)

    def _execute_gemini_agent(self, user_input: str, text: str, extracted_entity: str = None) -> str:
        if "explain " in text:
            topic = extracted_entity if extracted_entity else text.split("explain ")[-1].strip().rstrip('?.!')
            return self.gemini_agent.explain(topic)
        if "compare " in text or " vs " in text or " versus " in text:
            item1, item2 = "", ""
            if "compare " in text:
                parts = text.replace("compare ", "").split(" and ")
            elif " vs " in text:
                parts = text.split(" vs ")
            else:
                parts = text.split(" versus ")
            if len(parts) == 2:
                item1 = self._clean_extracted_entity(parts[0].strip())
                item2 = self._clean_extracted_entity(parts[1].strip().rstrip('?.!'))
            if item1 and item2:
                return self.gemini_agent.compare(item1, item2)
        if "summarize " in text:
            target_text = extracted_entity if extracted_entity else text.split("summarize ")[-1].strip()
            return self.gemini_agent.summarize(target_text)
        return self.gemini_agent.handle(user_input)

    def _execute_selected_intelligence_agent(self, selected_agent: str, user_input: str, normalized_query: str, extracted_entity: str = None):
        agent_names = {
            "weather": "WeatherAgent",
            "dictionary": "DictionaryAgent",
            "wikipedia": "WikipediaAgent",
            "news": "NewsAgent",
            "reasoning": "GeminiAgent",
        }
        if selected_agent == "weather":
            return self._execute_weather_agent(normalized_query, extracted_entity), agent_names[selected_agent]
        if selected_agent == "dictionary":
            return self._execute_dictionary_agent(normalized_query, extracted_entity), agent_names[selected_agent]
        if selected_agent == "wikipedia":
            return self._execute_wikipedia_agent(normalized_query, extracted_entity), agent_names[selected_agent]
        if selected_agent == "news":
            return self._execute_news_agent(normalized_query, extracted_entity), agent_names[selected_agent]
        return self._execute_gemini_agent(user_input, normalized_query, extracted_entity), agent_names["reasoning"]

    def _run_intelligence_query(self, user_input: str):
        """
        Routes a query to the selected agent based on centralized intent analysis,
        context resolution, entity extraction, response validation, and fallbacks.
        """
        import time
        start_time = time.perf_counter()
        
        # ── LOCAL SOCIAL INTERCEPTS ───────────────────────────────────────────
        text_check = user_input.lower().strip().rstrip('.')
        SOCIAL_RESPONSES = {
            "thank you":     "Always a pleasure, boss.",
            "thanks":        "Of course, boss.",
            "thank you so much": "Glad I could help, boss.",
            "cool":          "Glad you think so, boss.",
            "got it":        "Great, boss. Anything else?",
            "nice":          "Happy to help, boss.",
            "awesome":       "Glad to be useful, boss.",
            "great":         "Good to hear, boss. What's next?",
            "okay":          "Understood, boss.",
            "ok":            "Noted, boss.",
            "thanks a lot":   "You're welcome, boss.",
            "hm":            "anything else, boss?",
            "hmm":           "Yes, boss? What else can I do for you?",
            "alright":       "Alright, boss. What else can I help with?",
            "i see":         "Good. Let me know if you have more questions, boss.",
            "interesting":   "I am glad you find it interesting, boss.",
        }
        if text_check in SOCIAL_RESPONSES:
            local_reply = SOCIAL_RESPONSES[text_check]
            print(f"[INTEL MODE] Local intercept: '{text_check}' -> '{local_reply}'")
            self.gui.log_message("Smaran", local_reply)
            self.speak(local_reply, "Intelligence Mode")
            if self.gui:
                self.state_manager.set_state("intel_active")
            self.gui.root.after(600, self.start_active_listening)
            return

        # 1. Intent Analysis
        intent, intent_confidence = self._analyze_intent(user_input)
        
        # 2. Context Resolution (Pronoun Substitution)
        resolved_query, resolved_agent = self._resolve_context(user_input, intent)
        
        normalized_query = self._preprocess_router_query(resolved_query)
        
        selected_agent = None
        selected_agent_confidence = 0.0
        routing_reason = ""
        
        if resolved_agent:
            selected_agent = resolved_agent
            selected_agent_confidence = 1.0
            routing_reason = "Context resolution (pronoun mapped to previous topic)"
        elif normalized_query.startswith("hey smaran"):
            selected_agent = "reasoning"
            selected_agent_confidence = 1.0
            routing_reason = "Direct routing due to 'hey smaran' prefix"
        else:
            scores = self._score_intelligence_agents(normalized_query)
            winner, highest_score, second_highest_score, confidence_gap = self._select_agent_by_confidence(scores)
            
            if winner is not None:
                selected_agent = winner
                selected_agent_confidence = round(confidence_gap / highest_score if highest_score > 0 else 0.0, 2)
                routing_reason = f"Keyword match with confidence gap {confidence_gap}"
            else:
                routing_reason = "Ambiguous local score; classified with Gemini"
                selected_agent = self._classify_with_gemini(resolved_query)
                selected_agent_confidence = 0.8
                
        agent_names = {
            "weather": "WeatherAgent",
            "dictionary": "DictionaryAgent",
            "wikipedia": "WikipediaAgent",
            "news": "NewsAgent",
            "reasoning": "GeminiAgent",
        }
        agent_name_for_log = agent_names.get(selected_agent, "GeminiAgent")
        print(f"[INTEL]\nSelected Agent: {agent_name_for_log}\nConfidence: {selected_agent_confidence}\nReason: {routing_reason}")

        # 3. Central Entity Extraction
        extracted_entity = self._extract_entity(resolved_query, selected_agent)
        
        # Track context if entity is extracted successfully
        if extracted_entity and selected_agent in ("weather", "dictionary", "wikipedia", "news"):
            self.intel_context["last_entity"] = extracted_entity
            self.intel_context["last_agent"] = selected_agent
            
        # 4. Route and Execute
        response = None
        agent_executed = agent_name_for_log
        
        if self.gui:
            self.state_manager.set_state("thinking")
            
        try:
            response, agent_executed = self._execute_selected_intelligence_agent(
                selected_agent,
                resolved_query,
                normalized_query,
                extracted_entity
            )
        except Exception as e:
            print(f"[INTEL MODE ERROR] Selected agent {agent_executed} execution failed: {e}")
            response = None
            
        # 5. Response Validation & Fallback strategy
        is_valid = self._validate_response(response)
        
        if not is_valid:
            print(f"[INTEL MODE] Response from {agent_executed} invalid/error. Entering Fallback Strategy (Gemini Flash)...")
            try:
                print(f"[INTEL MODE] Querying Gemini as central fallback...")
                response = self.gemini_agent.query_with_history(resolved_query, self.intel_history)
                agent_executed = "GeminiAgent"
                is_valid = self._validate_response(response)
            except Exception as e:
                print(f"[INTEL MODE] Gemini fallback failed: {e}")
                response = None
                is_valid = False

        if not is_valid or response is None:
            response = "Sorry boss, reasoning engines are currently unavailable."
            agent_executed = "System"

        # Apply voice-friendly formatting and boss-address filter
        response = re.sub(r'\bsir\b', 'boss', response, flags=re.IGNORECASE)
        response = re.sub(r'\bmam\b', 'boss', response, flags=re.IGNORECASE)
        response = re.sub(r'\bmadam\b', 'boss', response, flags=re.IGNORECASE)
        
        spoken_response = self._make_voice_friendly(response)
        
        if agent_executed in ("GeminiAgent", "Groq") and not response.startswith("Sorry boss"):
            self.intel_history.append({"role": "user", "content": resolved_query})
            self.intel_history.append({"role": "assistant", "content": response})
            if len(self.intel_history) > 20:
                self.intel_history = self.intel_history[-20:]

        self.gui.log_message("Smaran", spoken_response)
        print(f"[INTEL MODE] {agent_executed} Response: {spoken_response}")
        self.speak(spoken_response, "Intelligence Mode")
        
        if self.gui:
            self.state_manager.set_state("intel_active")
            
        execution_time_ms = int((time.perf_counter() - start_time) * 1000)
        print(f"[INTEL]\nExecution Time: {execution_time_ms}ms | Response Length: {len(spoken_response)} chars")
        
        self.gui.root.after(600, self.start_active_listening)

    # ─────────────────────────────────────────────────────────────────────────

    def play_chime(self, chime_type):
        """Helper to play audio cues through speakers/headphones via WAV files."""
        def _play():
            try:
                import winsound

                # Resolve WAV candidates in order of preference
                WAV_CANDIDATES = [
                    r"C:\Windows\Media\Windows Notify System Generic.wav",
                    r"C:\Windows\Media\Windows Notify.wav",
                    r"C:\Windows\Media\Windows Unlock.wav",
                    r"C:\Windows\Media\Windows Ding.wav",
                    r"C:\Windows\Media\ding.wav",
                    r"C:\Windows\Media\chimes.wav",
                ]

                if chime_type == "listening":
                    for wav in WAV_CANDIDATES:
                        if os.path.exists(wav):
                            winsound.PlaySound(wav, winsound.SND_FILENAME | winsound.SND_NODEFAULT)
                            return
                    # Last resort fallback
                    winsound.Beep(1800, 120)

                elif chime_type == "wake":
                    for wav in WAV_CANDIDATES:
                        if os.path.exists(wav):
                            winsound.PlaySound(wav, winsound.SND_FILENAME | winsound.SND_NODEFAULT)
                            return
                    winsound.Beep(2000, 100)

            except Exception as e:
                print(f"[CHIME ERROR] Could not play chime: {e}")

        threading.Thread(target=_play, daemon=True).start()

    def handle_voice_change(self):
        if self.gui:
            gender = self.gui.voice_gender.get()
            self.voice.set_voice_gender(gender)

    def start_active_listening(self):
        """Arms background listener cleanly to process voice commands"""
        if not self.mic:
            return
        # Do NOT restart listening while Quiet Mode is active
        if self.quiet_mode:
            print("[QUIET MODE] start_active_listening suppressed — Quiet Mode is active.")
            return
        if self.stop_listening_fn is not None:
            return  # Already listening
            
        self.play_chime("listening")
        print("🎤 [MIC ACTIVE] Listening...")
        if self.gui:
            self.state_manager.set_state("listening")
            
        # Offload blocking calibration and listener arming to background thread
        threading.Thread(target=self._async_start_listening, daemon=True).start()

    def _async_start_listening(self):
        # Acquire lock — only one listener can start at a time
        if not self._mic_lock.acquire(blocking=False):
            print("⚠️ [MIC] Start skipped — another listener is already starting.")
            return
        try:
            # Brief pause to let the OS fully release the audio device from the previous session
            time.sleep(0.35)
            
            if self.stop_listening_fn is not None:
                print("⚠️ [MIC] Start skipped — listener already active.")
                return
            
            # Create a FRESH Microphone instance every session.
            # Reusing one shared instance causes AssertionError when the old
            # listen_in_background thread hasn't fully released the context manager yet.
            fresh_mic = sr.Microphone()
            
            self.stop_listening_fn = self.recognizer.listen_in_background(
                fresh_mic,
                self.active_listening_callback,
                phrase_time_limit=25
            )
            print("🎤 [MIC ARMED] Background listener is active.")
        except Exception as e:
            print(f"⚠️ [MIC ERROR] Could not start background listening: {e}")
            if self.gui:
                self.state_manager.set_state("error")
        finally:
            self._mic_lock.release()
            
    def stop_active_listening(self):
        """Disarms active microphone listener to prevent concurrent audio conflict"""
        fn = self.stop_listening_fn
        if fn is not None:
            print("🔇 [MIC DEACTIVATED] Stopping listener...")
            self.stop_listening_fn = None
            try:
                # wait_for_stop=True ensures the internal thread fully exits and releases
                # the mic context manager before we try to open it again
                fn(wait_for_stop=True)
            except Exception as e:
                print(f"[MIC STOP WARNING] {e}")


    def _check_quiet_command(self, text: str):
        """
        Checks if the text is a Quiet Mode activation or deactivation command.
        Returns: 'enter_quiet' | 'exit_quiet' | None

        Voice Activation : 'quiet', 'go quiet', 'enter quiet mode', 'quiet mode'
        Text / Voice Exit: 'resume', 'resume listening', 'exit quiet mode'
        Uses fuzzy matching to handle Whisper transcription errors.
        """
        from difflib import SequenceMatcher
        t = text.lower().strip()

        exit_phrases = [
            "resume", "resume listening", "exit quiet mode",
            "exit quiet", "disable quiet mode", "stop quiet mode",
        ]
        activate_phrases = [
            "quiet", "go quiet", "enter quiet mode",
            "go to quiet", "quiet mode", "silence mode",
        ]

        def fuzzy(a, b, threshold=0.85):
            if a == b:
                return True
            aw, bw = a.split(), b.split()
            for i in range(len(aw) - len(bw) + 1):
                if aw[i:i + len(bw)] == bw:
                    return True
            return SequenceMatcher(None, a, b).ratio() >= threshold

        # Check exit first to avoid misrouting "exit quiet mode" as activation
        for phrase in exit_phrases:
            if fuzzy(t, phrase):
                return "exit_quiet"
        for phrase in activate_phrases:
            if fuzzy(t, phrase):
                return "enter_quiet"
        return None

    def active_listening_callback(self, recognizer, audio):
        """Triggered by background listener thread when a phrase is captured"""
        # Guard 1: Drop audio captured DURING TTS playback
        if self.is_speaking:
            print("[MIC GUARD] Discarding audio captured during TTS playback.")
            return
        # Guard 2: Post-speech cooldown — discard room echo for 3.5s after TTS ends.
        # Most room echoes fully fade within 3 seconds. 3.5s gives safe margin.
        elapsed = time.time() - self.speech_finished_at
        if elapsed < 3.5:
            print(f"[MIC GUARD] Post-speech cooldown ({elapsed:.2f}s < 3.5s). Discarding echo.")
            return
        # NOTE: Do NOT stop listening here — we stop it inside process_audio_directive

        if self.gui:
            self.state_manager.set_state("thinking", "Processing...")
        threading.Thread(target=self.process_audio_directive, args=(audio,), daemon=True).start()

    def process_audio_directive(self, audio):
        """Performs speech recognition on captured audio chunk and passes it to pipeline"""
        # Stop listening here — AFTER we have the audio data — so Whisper processes
        # one command at a time without the mic picking up Smaran's own voice.
        self.stop_active_listening()
        
        try:
            print("👂 [PROCESSING ACTIVE DIRECTIVE] Recognizing speech...")
            
            command_text = self.transcriber.transcribe(audio, mode="accurate").lower()
            # Strip trailing punctuation Whisper always adds (e.g. "open notepad." -> "open notepad")
            # Whisper appends periods, commas, question marks to all outputs by design.
            import re as _repunc
            command_text = _repunc.sub(r'[^\w\s]', ' ', command_text).strip()
            command_text = ' '.join(command_text.split())  # Collapse multiple spaces
            print(f"👂 [DIRECTIVE CAPTURED] Executing voice line: '{command_text}'")


            # ── NOISE FILTER LAYER 1: Repetition Guard ────────────────────────
            # Catches "okay okay okay" style echo loops (same word ≥ 4 times).
            import re as _re
            words_only = _re.sub(r'[^\w\s]', '', command_text).split()
            if len(words_only) >= 4:
                most_common = max(set(words_only), key=words_only.count) if words_only else ""
                repeat_ratio = words_only.count(most_common) / len(words_only)
                if repeat_ratio >= 0.70:
                    print(f"[NOISE FILTER] Repetition echo detected ('{most_common}' x{words_only.count(most_common)}). Discarding.")
                    if self.gui:
                        self.state_manager.set_state("listening", "Listening...")
                    self.gui.root.after(400, self.start_active_listening)
                    return

                # Bigram repetition guard to catch multi-word loops (e.g. "all right", "i get it")
                bigrams = [(words_only[i], words_only[i+1]) for i in range(len(words_only) - 1)]
                from collections import Counter as _Counter
                bigram_counts = _Counter(bigrams)
                MATH_OR_NUMBERS = {
                    "plus", "minus", "times", "divided", "by", "multiplied", "multiply", "add", "subtract",
                    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
                    "hundred", "thousand", "million", "billion", "and"
                }
                for (w1, w2), count in bigram_counts.items():
                    if count >= 3:
                        is_w1_conv = w1.isalpha() and w1.lower() not in MATH_OR_NUMBERS
                        is_w2_conv = w2.isalpha() and w2.lower() not in MATH_OR_NUMBERS
                        if is_w1_conv and is_w2_conv:
                            print(f"[NOISE FILTER] Repeated bigram echo detected ('{w1} {w2}' x{count}). Discarding.")
                            if self.gui:
                                self.state_manager.set_state("listening", "Listening...")
                            self.gui.root.after(400, self.start_active_listening)
                            return

            # ── NOISE FILTER LAYER 2: Empty Guard ─────────────────────────────
            # Discard inputs with zero real words (punctuation-only, blank audio).
            if len(words_only) < 1:
                print(f"[NOISE FILTER] Empty input: '{command_text}'. Discarding.")
                if self.gui:
                    self.state_manager.set_state("listening", "Listening...")
                self.gui.root.after(400, self.start_active_listening)
                return

            # ── NOISE FILTER LAYER 3: Single-Word Echo Blocklist ──────────────
            # Single-word TTS artifacts that are NEVER real user commands.
            ECHO_WORDS = {
                "okay", "ok", "yeah", "yep", "yup", "nope",
                "yes", "no", "right", "sure", "alright",
                "um", "uh", "ah", "oh", "hmm", "hm",
                "well", "so", "now", "then", "just",
                "the", "a", "an", "and", "but", "or",
            }
            if len(words_only) == 1 and words_only[0] in ECHO_WORDS:
                print(f"[NOISE FILTER] Single-word echo artifact: '{words_only[0]}'. Discarding.")
                if self.gui:
                    self.state_manager.set_state("listening", "Listening...")
                self.gui.root.after(400, self.start_active_listening)
                return

            # ──────────────────────────────────────────────────────────────────

            self.gui.log_message("User", command_text)
            
            # Execute command pipeline
            self._async_pipeline(command_text)
            
        except (sr.WaitTimeoutError, sr.UnknownValueError):
            print("⚠️ [MIC TIMEOUT] Voice unclear or mic timed out. Restarting listener...")
            if self.gui:
                self.state_manager.set_state("listening")
            # Restart quickly — 800ms is enough for Smaran to finish speaking the error message
            self.gui.root.after(800, self.start_active_listening)
        except Exception as e:
            print(f"⚠️ [MIC ERROR] {e}")
            if self.gui:
                self.state_manager.set_state("error")
            self.gui.root.after(1500, self.start_active_listening)


    def pipeline(self, user_input):
        """Entry point for manual GUI text box inputs"""
        print(f"🎤 [USER INPUT RECEIVED (TEXT)] {user_input}")
        self.wake_triggered = True  # Bypass passive radar scanning

        # ── QUIET MODE EXIT — TEXT INPUT ───────────────────────────────────
        if self.quiet_mode:
            quiet_cmd = self._check_quiet_command(user_input)
            if quiet_cmd == "exit_quiet":
                self.quiet_mode = False
                print("[QUIET MODE] Deactivated via text input. Resuming listening.")
                if self.gui:
                    self.state_manager.set_state("listening")
                self.speak("Listening restored, boss.", "Listening")
                self.gui.root.after(600, self.start_active_listening)
                return
            else:
                # Still in quiet mode — process typed command normally through the pipeline
                pass
        # ──────────────────────────────────────────────────────────────────

        # Stop listening if we were actively listening, since the user is typing
        self.stop_active_listening()
        if self.gui:
            self.state_manager.set_state("thinking")
        
        # Run pipeline asynchronously to prevent GUI freeze
        threading.Thread(target=self._async_pipeline, args=(user_input,), daemon=True).start()

    def get_executing_task_desc(self, intent):
        action = intent.get("action")
        target = intent.get("target", "").lower()
        parameter = intent.get("parameter", "")
        
        if action == "launch_app":
            if target in ["chrome", "msedge", "firefox", "opera", "brave", "browser", "operagx", "opera gx"]:
                display_browser = "Chrome" if target in ["browser", "chrome"] else target.capitalize()
                if "gx" in target.lower():
                    display_browser = "Opera GX"
                if parameter and parameter != "none":
                    if parameter.startswith("youtube "):
                        return "Opening YouTube..."
                    else:
                        return "Searching Google..."
                return f"Opening {display_browser}..."
            elif target == "notepad":
                return "Opening Notepad..."
            elif target == "calculator":
                return "Opening Calculator..."
            elif target == "cmd":
                return "Opening Command Prompt..."
            elif target == "explorer":
                return "Opening File Explorer..."
            elif target == "task manager":
                return "Opening Task Manager..."
            else:
                return f"Opening {target.capitalize()}..."
        elif action == "system_control":
            if target == "volume_up":
                return "Increasing Volume..."
            elif target == "volume_down":
                return "Decreasing Volume..."
            elif target == "mute":
                return "Muting Audio..."
            return "Adjusting Volume..."
        elif action == "shutdown":
            return "Shutting Down..."
        elif action == "weather_scanner":
            return "Scanning Weather..."
        elif action == "morning_briefing":
            return "Preparing Briefing..."
        elif action == "ecosystem_workspace":
            return "Launching Workspaces..."
        elif action == "youtube_music":
            return "Opening YouTube Music..."
        elif action == "random_generator":
            return "Generating Value..."
        elif action == "wisdom_vault":
            return "Retrieving Quote..."
        elif action == "countdown_timer":
            return "Calculating Countdown..."
        elif action == "calculator_compute":
            return "Computing Result..."
        elif action == "grok_query":
            return "Thinking..."
        return "Executing..."

    def _async_pipeline(self, user_input):
        """Runs brain process, speaks response, executes OS command, and restarts listening"""
        print(f"🎤 [USER INPUT RECEIVED] {user_input}")
        if self.gui:
            self.gui.is_music_active = False

        text = user_input.lower().strip()

        # ── QUIET MODE COMMAND CHECK ────────────────────────────────────
        # Checked before intelligence mode and automation routing.
        quiet_cmd = self._check_quiet_command(text)

        if quiet_cmd == "enter_quiet":
            if self.quiet_mode:
                self.speak("Quiet Mode is already active, boss.", "Quiet Mode")
                self.gui.root.after(600, self.start_active_listening)
                return
            self.quiet_mode = True
            self.stop_active_listening()  # Halt mic immediately
            print("[QUIET MODE] Activated. Microphone suspended.")
            if self.gui:
                self.state_manager.set_state("quiet")
            self.speak(
                "Entering Quiet Mode, boss. Microphone is now suspended. "
                "Use the text box and type 'resume' to restore listening.",
                "Quiet Mode"
            )
            if self.gui:
                self.state_manager.set_state("quiet")
            # Do NOT call start_active_listening -- mic stays off until user exits
            return

        if quiet_cmd == "exit_quiet":
            if not self.quiet_mode:
                self.speak("Quiet Mode is not active, boss.", "Automation")
                self.gui.root.after(600, self.start_active_listening)
            else:
                self.quiet_mode = False
                print("[QUIET MODE] Deactivated. Resuming listening.")
                if self.gui:
                    self.state_manager.set_state("listening")
                self.speak("Listening restored, boss.", "Listening")
                self.gui.root.after(600, self.start_active_listening)
            return
        # ──────────────────────────────────────────────────────────────────

        # ── INTELLIGENCE MODE COMMAND CHECK ─────────────────────────────────
        # Always checked first -- works from both Automation and Intelligence Mode.
        intel_cmd = self._check_intel_command(text)

        if intel_cmd == "activate":
            if self.intelligence_mode:
                # Already in intelligence mode
                self.speak("Intelligence Mode is already active, boss.", "Intelligence Mode")
            else:
                self.intelligence_mode = True
                self.intel_history = []   # Fresh history for each session
                print("[INTEL MODE] Activated. All prompts now route to Groq.")
                if self.gui:
                    self.state_manager.set_state("intel_active")
                self.speak(
                    "Intelligence Mode activated, boss. I am now in full reasoning mode. "
                    "Ask me anything — I will maintain context throughout our conversation. "
                    "Say 'Lock Intelligence' or 'Deactivate Intelligence' to return to Automation Mode.",
                    "Intelligence Mode"
                )
                if self.gui:
                    self.state_manager.set_state("intel_active")
            self.gui.root.after(600, self.start_active_listening)
            return

        if intel_cmd == "deactivate":
            if not self.intelligence_mode:
                self.speak("Automation Mode is already active, boss.", "Automation")
            else:
                self.intelligence_mode = False
                self.intel_history = []   # Clear history on exit
                print("[INTEL MODE] Deactivated. Returning to Automation Mode.")
                if self.gui:
                    self.state_manager.set_state("idle")
                self.speak(
                    "Intelligence Mode locked, boss. Returning to Automation Mode. "
                    "All standard commands are active again.",
                    "Automation Mode"
                )
                if self.gui:
                    self.state_manager.set_state("idle")
            self.gui.root.after(600, self.start_active_listening)
            return
        # ─────────────────────────────────────────────────────────────────────

        # ── INTELLIGENCE MODE — OS COMMANDS BYPASS GROQ ──────────────────────
        # Even in Intelligence Mode, OS automation commands must be handled
        # locally. We run the brain first; only genuine knowledge queries go
        # to the intelligence agents. This fixes commands like
        # "set timer for 45 minutes" or "open notepad" being wrongly sent to Grok.
        if self.intelligence_mode:
            # Define which actions are pure OS automation (must never go to Groq)
            OS_ACTIONS = {
                "launch_app", "system_control", "calculator_compute",
                "morning_briefing", "ecosystem_workspace",
                "youtube_music", "random_generator", "wisdom_vault",
                "countdown_timer", "set_clock_timer", "study_mode", "developer_mode", "fun_mode", "deep_mode", "shutdown",
                "activate_vision", "deactivate_vision",
            }
            _brain_intent = self.brain.think(user_input)
            _brain_action = _brain_intent.get("action", "")
            if _brain_action in OS_ACTIONS:
                # Handle as a local OS command — completely skip intelligence agents
                print(f"[INTEL MODE] OS action intercepted: '{_brain_action}' — routing locally.")
                # Push back into the normal automation pipeline by overriding structured_intent
                structured_intent = _brain_intent
                action = _brain_action
                # Jump past the intelligence routing block and process normally
                # (fall through to the spoken_text / OS dispatch section below)
            else:
                # It's a knowledge query — route to intelligence agents as normal
                self._run_intelligence_query(user_input)
                return
        # ─────────────────────────────────────────────────────────────────────

        if not self.intelligence_mode:
            # Normal Automation Mode: ask the brain
            structured_intent = self.brain.think(user_input)
            action = structured_intent.get("action")
            
            # Intercept "research " or "wikipedia" in Automation Mode to query WikipediaAgent directly
            if "research " in text or "wikipedia" in text:
                extracted_topic = self._extract_entity(user_input, "Research")
                if extracted_topic:
                    print(f"[AUTOMATION] Research query intercepted. Routing topic '{extracted_topic}' to WikipediaAgent...")
                    if self.gui:
                        self.state_manager.set_state("thinking")
                    response = self._execute_wikipedia_agent(extracted_topic)
                    
                    response = re.sub(r'\bsir\b', 'boss', response, flags=re.IGNORECASE)
                    response = re.sub(r'\bmam\b', 'boss', response, flags=re.IGNORECASE)
                    response = re.sub(r'\bmadam\b', 'boss', response, flags=re.IGNORECASE)
                    spoken_response = self._make_voice_friendly(response)
                    
                    self.gui.log_message("Smaran", spoken_response)
                    print(f"[AUTOMATION] WikipediaAgent Response: {spoken_response}")
                    self.speak(spoken_response, "Responding...")
                    if self.gui:
                        self.state_manager.set_state("success")
                    self.gui.root.after(800, self.start_active_listening)
                    return
        else:
            # We already set structured_intent above (OS action intercept path)
            action = structured_intent.get("action")


        # ── GROQ REASONING HANDLER ───────────────────────────────────────────
        # Handled separately before the rest of the pipeline since Groq
        # generates the spoken_response itself (not pre-baked by the brain).
        if action == "grok_query":
            query_text = structured_intent.get("parameter", user_input)
            print(f"[REASONING] Routing to Gemini Flash: '{query_text[:60]}'")
            if self.gui:
                self.state_manager.set_state("thinking")
            try:
                response = self.gemini_agent.ask(query_text)
                source = "gemini"
                if "unavailable" in response.lower() or "didn't understand" in response.lower():
                    raise ValueError("Gemini returned error response")
            except Exception as e:
                print(f"[REASONING] Gemini Flash failed ({e}).")
                response = "Sorry boss, I was unable to retrieve that information right now."
                source = "error"
            
            # Apply boss address replacement
            response = re.sub(r'\bsir\b', 'boss', response, flags=re.IGNORECASE)
            response = re.sub(r'\bmam\b', 'boss', response, flags=re.IGNORECASE)
            response = re.sub(r'\bmadam\b', 'boss', response, flags=re.IGNORECASE)
            
            self.gui.log_message("Smaran", response)
            print(f"🐼 [SMARAN/{source.upper()}] {response}")
            self.speak(response, "Responding...")
            if self.gui:
                if source == "error":
                    self.state_manager.set_state("error")
                else:
                    self.state_manager.set_state("success")
            
            # Restart listener after response regardless of success/failure
            self.gui.root.after(800, self.start_active_listening)
            return
        # ─────────────────────────────────────────────────────────────────────

        spoken_text = structured_intent.get("spoken_response", "Processing sequence.")
        
        # Replace address terms with 'boss' case-insensitively
        spoken_text = re.sub(r'\bsir\b', 'boss', spoken_text, flags=re.IGNORECASE)
        spoken_text = re.sub(r'\bmam\b', 'boss', spoken_text, flags=re.IGNORECASE)
        spoken_text = re.sub(r'\bmadam\b', 'boss', spoken_text, flags=re.IGNORECASE)
            
        self.gui.log_message("Smaran", spoken_text)
        print(f"🐼 [SMARAN SPEAKS] {spoken_text}")
        
        
        if action == "shutdown":
            if self.gui:
                self.state_manager.set_state("executing", "Shutting Down...")
            self.speak(spoken_text)
            
            # Play the same wake audio chime synchronously here on shutdown
            try:
                import winsound
                wav_path = getattr(self, 'wake_wav_path', None)
                if not wav_path or not os.path.exists(wav_path):
                    wav_path = r"C:\Windows\Media\Windows Unlock.wav"
                    if not os.path.exists(wav_path):
                        wav_path = r"C:\Windows\Media\Windows Logon.wav"
                    if not os.path.exists(wav_path):
                        wav_path = r"C:\Windows\Media\Windows Background.wav"
                    if not os.path.exists(wav_path):
                        wav_path = r"C:\Windows\Media\chimes.wav"
                winsound.PlaySound(wav_path, winsound.SND_FILENAME)
            except Exception as e:
                print(f"[SHUTDOWN AUDIO ERROR] {e}")

            print("🔌 [SMARAN] Shutting down systems...")
            if self.gui:
                self.gui.root.after(0, self.gui.root.destroy)
            time.sleep(0.1)
            os._exit(0)
            return
            
        elif action == "conversational_reply":
            is_fallback = "sorry i didnt understand" in spoken_text.lower()
            if is_fallback:
                if self.gui:
                    self.state_manager.set_state("error")
                # Use self.speak() — NOT self.voice.speak() — so is_speaking guard fires
                # and the mic stays suppressed during fallback TTS (prevents echo pickup)
                self.speak(spoken_text)
                if self.gui:
                    self.state_manager.set_state("idle")
                self.gui.root.after(800, self.start_active_listening)
            else:
                self.speak(spoken_text)
                if self.gui:
                    self.state_manager.set_state("success")
                self.gui.root.after(800, self.start_active_listening)
            return

        # ── STUDY MODE HANDLER ────────────────────────────────────────────────
        # Speaks activation phrase, runs the full OS workflow, then activates
        # Intelligence Mode so the user can ask questions during the study session.
        elif action == "study_mode":
            print("[STUDY MODE] Workflow triggered.")
            if self.gui:
                self.state_manager.set_state("executing", "Study Mode")
            # Speak activation announcement
            self.speak("Activating Study Mode boss.", "Study Mode")
            # Run OS-level workflow (close apps, open clock, lofi, Gemini, WhatsApp, Explorer)
            try:
                _, study_msg = self.os_control.activate_study_mode()
                print(f"[STUDY MODE] OS workflow result: {study_msg}")
            except Exception as e:
                print(f"[STUDY MODE] OS workflow error: {e}")
            # Announce Intelligence Mode activation
            time.sleep(1.5)
            self.speak("Activating Intelligence Mode boss.", "Study Mode")
            # Enable Intelligence Mode
            self.intelligence_mode = True
            self.intel_history = []
            print("[STUDY MODE] Intelligence Mode enabled.")
            if self.gui:
                self.state_manager.set_state("intel_active")
            # Final confirmation
            time.sleep(0.5)
            self.speak("study mode activated", "Study Mode")
            print("[STUDY MODE] Setup complete.")
            self.gui.root.after(800, self.start_active_listening)
            return

        # ── DEVELOPER MODE HANDLER ────────────────────────────────────────────
        elif action == "developer_mode":
            print("[DEVELOPER MODE] Workflow triggered.")
            if self.gui:
                self.state_manager.set_state("executing", "Developer Mode")
            self.speak("Activating Developer Mode boss.", "Developer Mode")
            try:
                _, dev_msg = self.os_control.activate_developer_mode()
                print(f"[DEVELOPER MODE] OS workflow result: {dev_msg}")
            except Exception as e:
                print(f"[DEVELOPER MODE] OS workflow error: {e}")
            time.sleep(1.5)
            self.speak("Activating Intelligence Mode boss.", "Developer Mode")
            self.intelligence_mode = True
            self.intel_history = []
            print("[DEVELOPER MODE] Intelligence Mode enabled.")
            if self.gui:
                self.state_manager.set_state("intel_active")
            time.sleep(0.5)
            self.speak("Dev Mode Activated", "Developer Mode")
            print("[DEVELOPER MODE] Setup complete.")
            self.gui.root.after(800, self.start_active_listening)
            return

        # ── FUN MODE HANDLER ──────────────────────────────────────────────────
        elif action == "fun_mode":
            print("[FUN MODE] Workflow triggered.")
            if self.gui:
                self.state_manager.set_state("executing", "Fun Mode")
            self.speak("Activating Fun Mode boss.", "Fun Mode")
            try:
                _, msg = self.os_control.activate_fun_mode()
                print(f"[FUN MODE] OS workflow result: {msg}")
            except Exception as e:
                print(f"[FUN MODE] OS workflow error: {e}")
            time.sleep(0.5)
            self.speak("Fun Mode Activated", "Fun Mode")
            print("[FUN MODE] Setup complete.")
            self.gui.root.after(800, self.start_active_listening)
            return

        # ── DEEP MODE HANDLER ─────────────────────────────────────────────────
        elif action == "deep_mode":
            print("[DEEP MODE] Workflow triggered.")
            if self.gui:
                self.state_manager.set_state("executing", "Deep Mode")
            self.speak("Activating Deep Mode boss.", "Deep Mode")
            try:
                _, msg = self.os_control.activate_deep_mode()
                print(f"[DEEP MODE] OS workflow result: {msg}")
            except Exception as e:
                print(f"[DEEP MODE] OS workflow error: {e}")
            time.sleep(0.5)
            self.speak("Deep Mode Activated", "Deep Mode")
            print("[DEEP MODE] Setup complete.")
            self.gui.root.after(800, self.start_active_listening)
            return
        # ─────────────────────────────────────────────────────────────────────
  
        task_desc = self.get_executing_task_desc(structured_intent)
        self.speak(spoken_text)  # Show "Speaking..." during confirmation
        
        # Determine if this is a music-related action to show the music expression
        is_music_action = (action == "youtube_music") or (action == "launch_app" and "youtube" in task_desc.lower())
        
        if self.gui:
            if is_music_action:
                self.gui.is_music_active = True
                self.state_manager.set_state("music", task_desc)
            else:
                self.state_manager.set_state("executing", task_desc)
        
        # Deliberate pause to show executing state step-by-step
        time.sleep(1.0)
        
        # Execute the intent on the operating system
        success, verification_msg = self.os_control.execute_command(structured_intent)
        
        if success:
            verification_msg = re.sub(r'\bsir\b', 'boss', verification_msg, flags=re.IGNORECASE)
            verification_msg = re.sub(r'\bmam\b', 'boss', verification_msg, flags=re.IGNORECASE)
            verification_msg = re.sub(r'\bmadam\b', 'boss', verification_msg, flags=re.IGNORECASE)
                
            # Speak the dynamic execution output for informational/algorithmic actions
            speak_actions = [
                "weather_scanner", "morning_briefing", "random_generator",
                "wisdom_vault", "countdown_timer", "set_clock_timer",
                "calculator_compute",   # Speak the computed result back to the user
                "activate_vision", "deactivate_vision",
            ]
            if action in speak_actions:
                self.gui.log_message("Smaran", verification_msg)
                print(f"🐼 [SMARAN SPEAKS] {verification_msg}")
                self.speak(verification_msg)  # Show "Speaking..." during verification output
                
            if self.gui:
                if is_music_action:
                    self.gui.is_music_active = True
                    self.state_manager.set_state("music", task_desc)
                else:
                    self.state_manager.set_state("success")
            self.gui.root.after(800, self.start_active_listening)
        else:
            verification_msg = re.sub(r'\bsir\b', 'boss', verification_msg, flags=re.IGNORECASE)
            verification_msg = re.sub(r'\bmam\b', 'boss', verification_msg, flags=re.IGNORECASE)
            verification_msg = re.sub(r'\bmadam\b', 'boss', verification_msg, flags=re.IGNORECASE)
                
            error_speak_actions = ["activate_vision", "deactivate_vision"]
            if action in error_speak_actions:
                self.gui.log_message("Smaran", verification_msg)
                print(f"🐼 [SMARAN SPEAKS] {verification_msg}")
                self.speak(verification_msg)
                
            if self.gui:
                self.state_manager.set_state("error")
            self.gui.root.after(1500, self.start_active_listening)
 
if __name__ == "__main__":
    assistant = SmaranCore()
