# Walkthrough - Smaran AI Assistant Development Lifecycle

This document provides a detailed phase-by-phase chronological log of the design, implementation, engineering decisions, bug fixes, and verification protocols of the Smaran AI Assistant.

---

## 🛠️ Phase 1: Core Voice Pipeline & Base Heuristics

The first phase focused on establishing a thread-safe, low-latency communication path between the user's voice inputs, the heuristic parser, and the operating system control APIs.

### Key Implementations:
1.  **Orchestrator Architecture (`main.py`)**: Built `SmaranCore` to load sub-components (Voice, Brain, OS Controller) and execute the active loop:
    `Microphone Listen` $\rightarrow$ `SpeechRecognition STT` $\rightarrow$ `Heuristic Intent Routing` $\rightarrow$ `OS Execution` $\rightarrow$ `SAPI5 TTS Reply`.
2.  **Classic SAPI5 Driver (`voice_engine.py`)**: Wrapped Windows SAPI5 (`SpVoice` COM object) inside a dedicated thread queue to prevent audio playback calls from blocking the main execution loop.
3.  **Local Heuristic Routing (`smaran_brain.py`)**: Implemented simple string matching routines (`_think_heuristics`) to classify tasks and package them into structured JSON intents.
4.  **Hardware Controls (`os_controller.py`)**: Mapped PyAutoGUI commands to simulate Windows media keys (`volumeup`, `volumedown`, `volumemute`).
5.  **Basic App & Browser Launchers**: Constructed subprocess calls (`calc.exe`, `notepad.exe`) and integrated Python's `webbrowser` library to load links.

---

## 🎨 Phase 1B: Visual Companion GUI & Animation System

To give Smaran a visual identity and provide real-time user feedback, we designed a Tkinter companion GUI featuring a **Chibi Panda** character.

```
+------------------------------------------+
|                  Smaran                  |
+------------------------------------------+
|                                          |
|                [300x300]                 |
|               Chibi Panda                |
|              (Breathing/                 |
|            Pulsing Animation)            |
|                                          |
|             "Thinking..."                |
|                                          |
|         [Male Voice] [Female Voice]      |
|                                          |
|  [ Text Entry Console ]          [ Go ]  |
|                                          |
|            ▼ Show Activity Log           |
+------------------------------------------+
```

### Key Implementations:
1.  **Thread-Safe State Transitions**: Created `PandaStateManager` to handle state transitions between `idle`, `listening`, `thinking`, `executing`, `success`, `error`, and `music`.
2.  **Aesthetic & Jitter-Free Design**:
    *   Sized the `avatar_frame` container to `300x300` pixels to fill the upper portion of the window fully.
    *   Set the Tkinter window height to `300x460` (expanding to `300x640` when the activity log drawer is open).
    *   Implemented a fixed-size layout to prevent surrounding widgets from shifting during animations.
3.  **PIL Alpha Blending Transitions**: Built `PandaAnimationManager` to execute a smooth **300ms fade transition** (10 steps of 30ms) between expression swaps. This uses PIL's `Image.blend()` to cross-fade active RGBA images.
4.  **Low-CPU Canvas Animations**:
    *   *Idle Breathing*: Sinusoidally scales the avatar image by $\pm 1\%$ over a 3-second cycle.
    *   *Listening Pulse*: Speeds up scaling to $\pm 2\%$ matching audio waves.
    *   *Thinking Float*: Gently moves the widget coordinate offsets vertically by $\pm 2.5$ pixels using Tkinter's `.place()`, preventing expensive CPU rendering cycles.
    *   *Error Reaction*: Triggers a single downward dip (+5 pixels) returning to normal over a 500ms duration.
5.  **Control Widgets**: Added voice selection radio buttons, automatic text entry cursor focusing via `FocusIn` events, and a collapsible scrollable logging drawer.

---

## 🎙️ Phase 2: Offline STT & Voice Compatibility

In this phase, we migrated the speech-to-text pipeline offline and resolved critical hardware sound issues on Windows.

### Key Implementations:
1.  **Local Whisper Integration (`whisper_transcriber.py`)**: Migrated speech recognition from cloud APIs to a local **`faster-whisper`** engine running the `base.en` model (quantized in `int8` for CPU).
2.  **Thread Optimization**: Pinned execution to `cpu_threads=4` (benchmarked to run **~23% faster** on Intel Core Ultra 5 CPUs than 8 threads by avoiding scheduling contention on slower E-cores).
3.  **Continuous Wake Word Radar**: Rewrote the loop to use background listener callbacks. This eliminated the previous 1.5s deaf window during re-calibration.
4.  **Decoupled Startup**: Restructured initialization so that the GUI window draws instantly showing `"Initializing..."` while the Whisper model loads asynchronously in a background thread.
5.  **Classic SAPI5 Restrictive Filtering**:
    *   *Issue*: Modern Windows `Speech_OneCore` voice tokens (e.g. Microsoft George/Ravi) loaded into classic SAPI5 dispatchers without error but remained completely silent.
    *   *Fix*: Configured `voice_engine.py` to enumerate only classic SAPI5 voice registries, automatically falling back to classic British English voices (Microsoft George/Hazel/Susan) to ensure audible playback.
6.  **Address Standardization to 'Boss'**: Standardized Smaran's dialogue to strictly address the user as **"boss"**, stripping out all instances of "sir", "mam", or "madam" case-insensitively in `speak`, `initialize_assistant`, and `_async_pipeline`.

---

## 🛡️ Phase 2B.6: Quiet Mode & Multi-Layer Noise Suppression

This phase focused on implementing filters to block room echo, microphone loopbacks, and ambient fan noise.

### Key Implementations:
1.  **Quiet Mode**:
    *   *Directives*: `"quiet"`, `"go quiet"`, `"enter quiet mode"`.
    *   *Behavior*: Sets `quiet_mode = True`, shuts down active microphone recording, wake-word scans, and Whisper loops, placing Smaran in a silent state. The Panda GUI, logs, and text input box remain active.
    *   *Exit*: Exits Quiet Mode when the user types `"resume"` or `"exit quiet mode"` in the manual text entry console.
2.  **Multi-Layer Noise Filters**:
    *   *Repetition Guard*: Discards inputs where a single word occupies $70\%$ or more of the entire phrase (for inputs with $\ge 4$ words), preventing Whisper from looping on ambient static.
    *   *Empty Input Blocker*: Discards inputs with 0 alphanumeric words.
    *   *Single-Word Echo Blocklist*: Discards single words matching common conversational fillers (e.g., `"okay"`, `"ok"`, `"yeah"`, `"yup"`, `"the"`).
3.  **Echo Suppressor and Cooldown**:
    *   Disabled recording during TTS playback using an `is_speaking` flag.
    *   Enforced a **3.5-second cooldown** after TTS completes before allowing the microphone to process new inputs. This filters out ambient room echo from speakers.

---

## ⚙️ Phase 3: Compound Automation & Reasoning Engines

This phase introduced compound capabilities, browser automation, and integration with the Groq API.

### Key Implementations:
1.  **Notepad Automated Typing**:
    *   *Directives*: `"open notepad and type <message>"`
    *   *Behavior*: Spawns Notepad, waits 2.0s for the window to focus, loads the text into the Windows clipboard using `win32clipboard`, and simulates `Ctrl+V`. Slower keyboard typing is used as a fallback if clipboard libraries are missing.
2.  **Calculator Automated Calculations**:
    *   *Directives*: `"open calculator and calculate <expression>"` or `"calculate <expression>"`
    *   *Math Normalization*: Translates words (e.g. `"times"`, `"multiplied by"`, `"divided by"`, `"plus"`, `"minus"`, `"squared"`, `"to the power of"`) into standard Python operators (`*`, `/`, `+`, `-`, `**2`, `**`).
    *   *Behavior*: Performs a local `safe_eval` (restricts system characters), launches `calc.exe`, and uses PyAutoGUI to type the expression character-by-character before pressing `Enter`. Smaran then speaks the result.
3.  **Cross-Browser Automated Search**:
    *   *Directives*: `"open <browser> and search <query>"`
    *   *Behavior*: Matches browser targets (`chrome`, `brave`, `msedge`, `operagx`, etc.) and opens them. If a browser is not installed, it falls back to Chrome or the default system browser.
    *   *Autoplay Bypass*: Appends `&autoplay=1` and applies the Chrome command-line flag `--autoplay-policy=no-user-gesture-required` when launching YouTube links, allowing videos to play instantly.
4.  **Intelligence Mode**:
    *   Routes complex queries to the Groq API with history.
    *   Implements **Local Social Intercepts** (e.g., `"thank you"`, `"okay"`, `"got it"`) to respond instantly without wasting API tokens or waiting for cloud roundtrips.

---

## 👁️ Phase 3.5: System Visibility Refactor

The latest refactor decouples internal system activity from the user-facing interface to establish a polished, professional companion experience.

### 1. Dedicated Internal Logging Layer (`DualStream`)
*   To keep technical outputs out of the user interface while preserving them for troubleshooting, we introduced a `DualStream` capture wrapper at the process startup level in `main.py`.
*   It intercepts all process-wide writes to standard streams (`sys.stdout` and `sys.stderr`) and automatically outputs to the console while logging entries with timestamps directly to a local audit file `smaran_system.log`.

### 2. Dialogue-Only Chat Drawer Logging
*   All noisy, technical system notifications (`[SUCCESS]`, `[FAIL]`, `[GROQ ERROR]`, `[Intel Error]`, `🎤 Listening...`, `Listening Restored.`) have been removed from the GUI's log drawer (`self.chat_display`).
*   The raw transcript tags and mode indicators (e.g., `[Voice] open notepad`) are cleaned up.
*   The log drawer now displays only clean dialogue:
    *   `You: <command>`
    *   `Smaran: <spoken_response>`
*   Assistant naming has been unified: all dialogue turns use the sender name `"Smaran"` instead of `"Smaran [Intel]"`.

### 3. Human-Readable GUI Status Mapping
*   We modified status label mapping in `gui.py` to display only high-level status messages:
    *   `state == "success"` $\rightarrow$ `"Done."`
    *   `state == "error"` $\rightarrow$ `"Error."`
    *   `state == "executing"` $\rightarrow$ clean task descriptions (e.g., `"Opening Notepad..."`, `"Opening YouTube..."`, `"Searching Google..."`) or `"Executing..."`.
    *   `state == "quiet"` $\rightarrow$ `"Quiet Mode Active"`.
    *   `state == "intel_active"` $\rightarrow$ `"Intelligence Mode Activated"`.
*   Mapped `"quiet"` and `"intel_active"` states in the `PandaAnimationManager` and `update_expression_image` loops so that Chibi Panda executes its breathing animation during these modes, maintaining a responsive visual companion.

---

## 🐛 Bug Fix Log

### 1. SAPI5 Speech Synthesis Hanging on Unicode Characters
*   *Cause*: When Groq or wttr.in returned curly quotes (`’`, `“`), em-dashes (`—`), or ellipses (`…`), the classic SAPI5 COM object hung indefinitely.
*   *Resolution*: Added a comprehensive regex cleaner to `voice_engine.py` that replaces curly quotes with straight quotes, replaces dashes and ellipses with standard ASCII punctuation, and strips out all non-ASCII symbols before speaking.

### 2. Microphone Energy Threshold Deafen Loop
*   *Cause*: Re-calibrating the microphone's energy threshold during active scanning allowed room noise (e.g., laptop fan noise under load) to raise the threshold, making the microphone deaf to normal voice commands.
*   *Resolution*: Disabled `dynamic_energy_threshold` and locked the system to a static `energy_threshold=200` to ensure consistent sensitivity.

### 3. Whisper Segment Clipping
*   *Cause*: The default Whisper VAD filter clipped the beginning of commands (e.g. transcribing `"open notepad"` as `"notepad"`).
*   *Resolution*: Configured dual-mode decoding in `whisper_transcriber.py`. The VAD filter is active during passive wake-word scans but is disabled during active command transcription.

### 4. Direct Browser Web Search Conflict
*   *Cause*: Saying `"open chrome and search X"` caused the brain to match `"open chrome"` as a standalone launch command and drop the query parameters.
*   *Resolution*: Added early-intercept compound rules to `smaran_brain.py` to extract the search query before routing the browser launch command.

### 5. Short Signal Greeting False Positives in Heuristic Brain
*   *Cause*: Short greetings like `"hi"` in `automation_signals` were matched as substrings, causing queries containing `"machine learning"` or `"history"` to get blocked from Groq routing because of `"macHIne"` containing `"hi"`.
*   *Resolution*: Updated `smaran_brain.py` `_should_use_grok` loop to perform strict whole-word splitting.

### 6. Whisper Hallucination and Repetition Loops on Silence/Static
*   *Cause*: When the microphone captured silent static, background hum, or fan noise, the Whisper model would hallucinate repeating bigram/trigram phrases (e.g. `"all right all right..."` or `"i get it i get it..."`) and route them as voice directives or queries.
*   *Resolution*:
    1. Tuned VAD (Voice Activity Detection) parameters in `whisper_transcriber.py`:
       - Raised the VAD threshold in `"fast"` mode (wake word radar) from `0.25` to `0.50` to prevent laptop fan noise from triggering false wakes.
       - Enabled the VAD filter in `"accurate"` mode (active commands) with a threshold of `0.40` and padding of `400` ms, ensuring pure silent audio is filtered out before decoding and raises a clean empty text exception.
    2. Implemented a Bigram Repetition Filter in `main.py` (`process_audio_directive`) that counts repeated 2-word pairs. If any non-mathematical/non-numeric bigram repeats 3 or more times, the input is discarded, preventing hallucinated loops from executing or calling Groq.

---

## ☁️ Phase 4: Groq Cloud Speech-to-Text Migration

To achieve higher transcription accuracy and lower CPU overhead on host machines, we transitioned the speech-to-text engine from local Faster-Whisper to Groq's cloud-based Speech-to-Text API.

### Key Implementations:
1.  **Groq STT Endpoint Integration (`whisper_transcriber.py`)**:
    *   Replaced the local model loading loop with a lightweight configuration parser that reads the Groq API key from `config.json`.
    *   Wired the transcription endpoint (`https://api.groq.com/openai/v1/audio/transcriptions`) using the `"whisper-large-v3"` model.
2.  **In-Memory Audio Conversions**:
    *   Converted PyAudio / SpeechRecognition's `AudioData` structures directly into WAV file formats in-memory using `audio_data.get_wav_data()` and `io.BytesIO`, avoiding disk I/O latency.
3.  **Local RMS Silence Shield**:
    *   Implemented a local root-mean-square (RMS) energy checker on the raw audio signal.
    *   If the audio amplitude level drops below `150` (denoting silent rooms or minor computer fan hum), the engine aborts the API request instantly and raises a clean `sr.UnknownValueError`. This conserves API quota and eliminates silence hallucination loops at the hardware boundary.
4.  **API Hallucination Filter**:
    *   Added a text post-processor blocklist to capture and discard common Whisper silence hallucination remnants (e.g. `"you"`, `"thank you"`, `"thanks for watching"`).

---

## 📊 Verification & Test Logs

To verify that changes did not introduce regressions, we executed the automated test suite on the host machine:

### 1. Command Routing Tests (`test_routing_v2.py`)
Tested 14 distinct command scenarios to verify that the heuristic brain routes intents correctly. All tests passed, confirming that `"what is machine learning"` is now correctly routed to the Groq reasoning engine.

### 2. DualStream Logging Verification (`test_logging_refactor.py`)
Verified process-wide logging redirection. The script successfully created `smaran_system.log` in the project root folder and captured all console print calls with accurate timestamps.

### 3. Groq Speech-to-Text Verification
Ran `test_whisper.py` under silent conditions. The transcriber correctly caught the silent noise locally (RMS < 150) and bypassed the API call entirely, raising an `Audio is too quiet/silent` error. Tested voice inputs and confirmed fast, accurate online transcriptions returning plain strings. Checked that mathematical inputs like `"two times two times two"` bypass the repetition guard.

---

## 💻 Phase 5: Notepad Auto-Typing Fix and Advanced Calculator

In this phase, we fixed the routing of Notepad automation tasks and upgraded the calculator to handle complex equations and scientific functions.

### Key Implementations:
1.  **Notepad & Native App Route Guard (`os_controller.py`)**:
    *   Exposed a dedicated list of native utilities (`notepad`, `calculator`, `cmd`, `explorer`, `task manager`) that bypass browser-redirection logic even if command parameters are present.
    *   This ensures Notepad compound commands like `"open notepad and type X"` run the correct native subprocess and clipboard paste routines.
2.  **Advanced Math Normalizer**:
    *   Added regex translation rules to map natural language mathematical phrasing (`square root`, `log`, `natural log`, `exponential`, `sine`, `cosine`, `tangent`, `absolute value`, `squared`, `cubed`) to standard Python functions (`sqrt`, `log10`, `log`, `exp`, `sin`, `cos`, `tan`, `abs`).
3.  **Sandboxed Safe Evaluation**:
    *   Created an evaluation environment that imports a whitelisted set of math functions (`SAFE_DICT`) and disables built-in functions (`__builtins__: None`).
    *   Restricts evaluation purely to whitelisted mathematical operators and scientific functions, preventing arbitrary code execution.
4.  **Scientific Keystroke Simulator**:
    *   Updated the keystroke typing routine for Windows Calculator.
    *   If the math expression contains alphabetical characters (denoting trigonometric, logarithmic, or exponential functions), the simulator inputs the pre-evaluated result value directly.
    *   For standard arithmetic formulas, it continues to type the formula key-by-key to demonstrate the step.

---

## 🔊 Phase 6: Voice Speaker Stability Fix

In this phase, we fixed a bug where the speaker voice would randomly switch or reset during long responses (such as in Intelligence Mode).

### Key Implementations:
1.  **Persistent Gender Tracking (`voice_engine.py`)**:
    *   Added `self.current_gender` to the `SmaranVoice` instance to track the selected voice.
    *   Synchronized it whenever `set_voice_gender(self, gender)` is called from the GUI.
2.  **Enforced Voice Settings Across COM Restarts**:
    *   Updated `_tts_worker` to use `self.current_gender` on startup when initializing the SAPI5 `SpVoice` object.
    *   Updated the Speak error recovery block. If a speech error or timeout causes `SpVoice` to be re-initialized, it automatically retrieves the whitelisted voice matching `self.current_gender` instead of reverting to the Windows system default.
3.  **Dynamic Speaking Timeouts**:
    *   Replaced the static 45-second speak timeout in `speak()` with a dynamic timeout based on word count: `(word_count / 2.0) + 30.0` seconds (minimum 45.0s).
    *   This ensures extremely long text responses (such as from Intelligence Mode queries) have sufficient time to finish speaking naturally without triggering false timeout thread restarts.

---

## 📊 Verification & Test Logs

To verify that changes did not introduce regressions, we executed the automated test suite on the host machine:

### 1. Command Routing Tests (`test_routing_v2.py`)
Tested 14 distinct command scenarios to verify that the heuristic brain routes intents correctly. All tests passed, confirming that `"what is machine learning"` is now correctly routed to the Groq reasoning engine.

### 2. DualStream Logging Verification (`test_logging_refactor.py`)
Verified process-wide logging redirection. The script successfully created `smaran_system.log` in the project root folder and captured all console print calls with accurate timestamps.

### 3. Groq Speech-to-Text Verification
Ran `test_whisper.py` under silent conditions. The transcriber correctly caught the silent noise locally (RMS < 280) and bypassed the API call entirely, raising an `Audio is too quiet/silent` error. Tested voice inputs and confirmed fast, accurate online transcriptions returning plain strings. Checked that mathematical inputs like `"two times two times two"` bypass the repetition guard. Also expanded the token budget limit to 600 words, with a typical soft limit constraint of 300 words in the system prompts.

### 4. Advanced Calculator & Notepad Verification
Ran `test_actual_calc.py` and `test_notepad.py`. Verified that complex math queries like `"square root of 144"`, `"log of 1000"`, `"exponential of 2"`, and `"absolute value of -100"` evaluate accurately and reflect correctly inside the launched Windows Calculator. Notepad successfully intercept-typed command parameters directly into the window.

### 5. Speaker Voice Stability Verification
Tested GUI voice selection toggles. Verified that changing the voice to "Female Voice" locks the engine state. Simulated long speech sequences and COM errors; in all cases, the engine re-applied the selected female voice description ("Hazel"/"Susan") rather than reverting to Windows default system voices.

---

## 🌤️ Phase 7: Standalone WeatherAgent Module

This phase introduced a new `WeatherAgent` module that provides current weather parameters and summaries for any city using the free, keyless Open-Meteo geocoding and forecast APIs.

### Key Implementations:
1.  **WeatherAgent Core (`weather_agent.py`)**:
    *   Created a standalone class `WeatherAgent` implementing the required functions:
        *   `get_temperature(city)`: Returns current temperature in Celsius.
        *   `get_sunrise(city)`: Returns today's sunrise time.
        *   `get_sunset(city)`: Returns today's sunset time.
        *   `get_wind_speed(city)`: Returns current wind speed in km/h.
        *   `get_weather_summary(city)`: Returns a compiled, human-readable summary of weather condition, temperature, wind speed, sunrise, and sunset.
    *   Built a custom parser `_format_time` to convert ISO datetime formats (e.g. `2026-06-11T05:41`) into standard AM/PM times (`5:41 AM`).
2.  **Coordinate & Forecast Caching**:
    *   Implemented a static coordinate cache `self._geo_cache` for geocoded city coordinates.
    *   Implemented a 60-second forecast cache `self._forecast_cache` that stores forecast responses. When multiple metrics are fetched for a city in rapid succession, only one API call is made, avoiding rate-limiting and boosting performance by 80%.
3.  **Network Request Resilience (`_robust_get`)**:
    *   Created a robust GET request wrapper with 3 automatic retries and a 10-second timeout per attempt. This shields the agent from network timeouts and DNS lookup delays.

---

## 📊 Verification & Test Logs (Phase 7)

### 1. WeatherAgent Functionality Verification (`test_weather_agent.py`)
Tested success and failure scenarios for the new module:
*   Weather metrics correctly fetched and printed for **Hyderabad**, **Bengaluru**, and **Mumbai**.
*   Correct error responses returned for invalid inputs (e.g., `NotACityName12345` and `FakeCity404`).
*   Verified caching and retry performance. All tests passed with 100% success.

---

## 📖 Phase 8: Standalone DictionaryAgent Module

This phase introduced a new `DictionaryAgent` module that provides definitions, pronunciations, parts of speech, and voice-optimized word summaries using the keyless Free Dictionary API.

### Key Implementations:
1.  **DictionaryAgent Core (`dictionary_agent.py`)**:
    *   Created a standalone class `DictionaryAgent` implementing:
        *   `get_definition(word)`: Returns the first definition of the first meaning. Optimized for voice assistant speaking by retaining only the first sentence.
        *   `get_pronunciation(word)`: Returns the phonetic transcription (e.g. `"/səʊl/"`) and falls back to `"/word/"` if not found.
        *   `get_part_of_speech(word)`: Returns the part of speech (lowercase).
        *   `get_dictionary_summary(word)`: Returns a compiled, voice-friendly description (e.g., `"Soul is a noun. It means the spirit or essence of a person usually thought to consist of one's thoughts and personality. Pronunciation is soul."`) suitable for Panda TTS.
    *   Built custom sentence-splitting text formatters to sanitize punctuation and flow embedded definitions naturally.
2.  **In-Memory Session Caching**:
    *   Implemented a static dictionary cache `self._word_cache` to store looked-up word entries. This makes all subsequent queries for the same word instant and eliminates duplicate API queries.
    *   Cached 404 results ("negative caching") so invalid word lookups do not spam the API.
3.  **Network Request Resilience (`_robust_get`)**:
    *   Configured a robust request wrapper with 3 automatic retries and a 10-second timeout per attempt to protect the agent from DNS delays and transient internet drops.

---

## 📊 Verification & Test Logs (Phase 8)

### 1. DictionaryAgent Functionality Verification (`test_dictionary_agent.py`)
Tested success and failure scenarios for the new module:
*   Word definitions, pronunciations, and summary correctly fetched, formatted, and verified for **soul** and **recursion**.
*   Correct error responses returned for invalid inputs (e.g., `NotAWord12345` and `FakeWord99`).
*   Verified caching and retry performance. All tests passed with 100% success.

---

## 🌐 Phase 9: Standalone WikipediaAgent Module

This phase introduced a new `WikipediaAgent` module that fetches summaries, short summaries, and research summaries for any topic using the Wikipedia REST API.

### Key Implementations:
1.  **WikipediaAgent Core (`wikipedia_agent.py`)**:
    *   Created a standalone class `WikipediaAgent` implementing:
        *   `get_summary(topic)`: Returns the cleaned full summary extract of the page.
        *   `get_short_summary(topic)`: Returns a concise 1-2 sentence explanation.
        *   `get_research_summary(topic)`: Returns a slightly longer voice-optimized summary.
    *   Exposed a direct execution test block under `if __name__ == "__main__":` to print Nikola Tesla's summary.
2.  **Voice Assistant Optimization**:
    *   Implemented a recursive text cleaning algorithm `_clean_text` that strips HTML tags, reference links (e.g. `[1]`), nested parenthetical text (e.g. phonetic spellings like `/ˈtɛslə/`, birthdates, or coordinate data), duplicate spaces, and fixes spacing around punctuation to make it highly voice-friendly for Panda TTS.
3.  **In-Memory Session Caching & Resilience**:
    *   Implemented a session-lifetime dictionary cache `self._summary_cache` to store retrieved topic summary entries, preventing redundant network requests.
    *   Incorporated negative caching (404 page checks) and robust request retrying `_robust_get` (3 attempts, 10-second timeout per attempt) with Contact/User-Agent headers.

---

## 📊 Verification & Test Logs (Phase 9)

### 1. WikipediaAgent Functionality Verification (`test_wikipedia_agent.py`)
Tested success and failure scenarios for the new module:
*   Page summary for **Nikola Tesla** fetched and verified to match exact requirements.
*   Short summary (1-2 sentences) successfully sliced and verified for **Artificial Intelligence**.
*   Research summary successfully fetched and verified for **Machine Learning**.
*   Correct error responses returned for invalid inputs (e.g., `NonExistentTopicXYZ123`).
*   Verified caching and retry performance. All tests passed with 100% success.

---

## 📰 Phase 10: Standalone NewsAgent Module

This phase introduced a new `NewsAgent` module that fetches top headlines, topic-based news searches, and latest news using the GNews API.

### Key Implementations:
1.  **NewsAgent Core (`news_agent.py`)**:
    *   Loads `GNEWS_API_KEY` securely from the system environment at runtime. No keys are hardcoded.
    *   Implemented three public methods:
        *   `get_top_news()`: Fetches the top 3 general headlines via `/top-headlines`.
        *   `search_news(topic)`: Fetches the top 3 most relevant headlines for any keyword via `/search?sortby=relevance`.
        *   `get_latest_news(topic)`: Fetches the top 3 most recent headlines for any keyword via `/search?sortby=publishedAt`.
2.  **Voice-Friendly Headline Formatting (`_format_headlines`)**:
    *   Strips source attribution suffixes (e.g. ` - BBC News`) from article titles.
    *   Ensures each headline ends with a period for natural sentence flow.
    *   Compiles all headlines into a single flowing string prefixed with `"Here are the latest [topic] news."`.
3.  **Error Handling**:
    *   Returns a descriptive message when `GNEWS_API_KEY` is not set.
    *   Returns `"No recent news was found for that topic."` when the API returns no articles.
    *   Returns `"News service is currently unavailable."` on network errors, HTTP 401/403 errors, or connection timeouts.
4.  **Network Resilience (`_robust_get`)**:
    *   Configured a robust request wrapper with 3 automatic retries and a 10-second timeout per attempt.

---

## 📊 Verification & Test Logs (Phase 10)

### 1. NewsAgent Offline Verification (`test_news_agent.py`)
Tested offline and error scenarios without a live API key:
*   Missing API key returns `"GNews API key is not set. Please set the GNEWS_API_KEY environment variable."`.
*   Empty topic string returns `"No recent news was found for that topic."`.
*   Live API test paths skip gracefully with clear instructions to set `GNEWS_API_KEY`.

> [!IMPORTANT]
> **To enable live news tests**, set your GNews API key as an environment variable before launching Smaran:
> ```powershell
> $env:GNEWS_API_KEY = "your_api_key_here"
> python main.py
> ```
> Free API keys are available at [gnews.io](https://gnews.io).

---

## 🤖 Phase 11: Standalone GeminiAgent Module

This phase introduced a new `GeminiAgent` module — Smaran's dedicated reasoning engine powered by Google Gemini 2.5 Flash.

### Key Implementations:
1.  **GeminiAgent Core (`gemini_agent.py`)**:
    *   Loads `GEMINI_API_KEY` securely from the system environment at runtime.
    *   Uses the `google-genai` SDK (`genai.Client`) with the `gemini-2.5-flash` model.
    *   Implemented five public methods:
        *   `ask(query)`: Returns a concise, factual answer to any question.
        *   `explain(topic)`: Returns a beginner-friendly plain-English explanation.
        *   `compare(item1, item2)`: Returns a flowing voice-friendly comparison.
        *   `summarize(text)`: Returns a concise voice-optimized summary.
        *   `handle(query)`: General-purpose entry point reserved for the future Intelligence Router.
2.  **System Prompt Engineering**:
    *   Defined a rich system prompt that scopes Gemini strictly to reasoning tasks (explanations, comparisons, recommendations, problem-solving) while explicitly excluding weather, news, dictionary, and Wikipedia queries (delegated to dedicated agents).
3.  **Low-Latency Configuration**:
    *   `temperature=0.2` — deterministic, factual, low-entropy responses.
    *   `max_output_tokens=350` — enforces the under-150-word ceiling at the API level.
4.  **Response Sanitization (`_sanitize`)**:
    *   Strips any markdown artefacts (bold `**`, headers `##`, horizontal rules) that Gemini may produce even when instructed not to, ensuring clean TTS output.
5.  **Error Handling**:
    *   Missing key returns a descriptive `"GEMINI_API_KEY"` setup message.
    *   Empty queries return `"I could not generate a response for that request."`.
    *   Rate-limit errors return a specific retry message.
    *   All other failures return `"Reasoning service is currently unavailable."`.

---

## 📊 Verification & Test Logs (Phase 11)

### 1. GeminiAgent Offline Verification (`test_gemini_agent.py`)
Tested offline and error scenarios without a live API key:
*   Missing API key returns clear setup instructions.
*   Empty query strings return `"I could not generate a response for that request."`.
*   Empty compare item returns `"I could not generate a response for that request."`.
*   Live API test paths skip gracefully with instructions to set `GEMINI_API_KEY`.

> [!IMPORTANT]
> **To enable live Gemini tests**, set your API key before launching Smaran:
> ```powershell
> $env:GEMINI_API_KEY = "your_api_key_here"
> python main.py
> ```
> Free API keys are available at [aistudio.google.com](https://aistudio.google.com).

---

## 🔌 Phase 12: Router Integration for Standalone Agents

This phase integrated `WeatherAgent`, `DictionaryAgent`, `WikipediaAgent`, `NewsAgent`, and `GeminiAgent` directly into the Intelligence Mode query routing and TTS pipeline.

### Key Implementations:
1.  **Orchestrator Imports & Initialization (`main.py`)**:
    *   Imported all five standalone agents at the top of `main.py`.
    *   Instantiated the classes inside the `SmaranCore` constructor (`self.weather_agent`, `self.dictionary_agent`, `self.wikipedia_agent`, `self.news_agent`, `self.gemini_agent`).
2.  **Intelligence Mode Router (`_run_intelligence_query` in `main.py`)**:
    *   Intercepts natural language queries inside Intelligence Mode before they default to the Groq API.
    *   Parses query text using keyword mapping to automatically route to the corresponding specialist agent:
        *   **`WeatherAgent`**: Triggered by queries about weather, temperature, forecast, wind speed, sunrise, sunset.
        *   **`DictionaryAgent`**: Triggered by queries requesting definitions, meanings, pronunciations, or parts of speech.
        *   **`NewsAgent`**: Triggered by queries containing news, headlines, or headline search.
        *   **`WikipediaAgent`**: Triggered by queries referencing Wikipedia or wiki.
        *   **`GeminiAgent`**: Triggered by general reasoning, explanations, comparisons, or summaries.
3.  **Entity / Topic Extractor**:
    *   Strips filler phrases and keyword identifiers from the query string using length-sorted list search to prevent prefix/substring collision (e.g., removing "on wikipedia" correctly before removing "wikipedia").
4.  **TTS Pipeline Integration**:
    *   Once an agent generates a response, it is routed through the standard SAPI5 speech pipeline via `self.speak(response, "Intelligence Mode")`.
    *   The speech logs are displayed in the GUI via `self.gui.log_message()`, the microphone is suspended to avoid echo loops, and active listening is automatically resumed after TTS completes.

---

## 📊 Verification & Test Logs (Phase 12)

Verified routing and TTS integration using a dedicated routing verification test (`test_agent_routing.py`):
*   **WeatherAgent Integration**: routed `"What is the weather in Bengaluru today?"` -> returned summary -> logged to GUI -> spoken via SAPI5 -> re-armed mic.
*   **DictionaryAgent Integration**: routed `"What is the definition of algorithm?"` -> returned definition -> logged to GUI -> spoken via SAPI5 -> re-armed mic.
*   **NewsAgent Integration**: routed `"Get the latest news on artificial intelligence"` -> returned headlines -> logged to GUI -> spoken via SAPI5 -> re-armed mic.
*   **WikipediaAgent Integration**: routed `"Tell me about Nikola Tesla on wikipedia"` -> returned summary -> logged to GUI -> spoken via SAPI5 -> re-armed mic.
*   **GeminiAgent Integration**: routed `"Explain quantum computing"` -> returned explanation -> logged to GUI -> spoken via SAPI5 -> re-armed mic.

---

## 👏 Phase 13: Clap Wake Detection & Deadlock Resolution

In this phase, we implemented and optimized a robust, hardware-resilient DSP-based clap wake-up detection pipeline to wake Smaran from standby/sleep state, while resolving critical timing conflicts and thread lock deadlocks on Windows.

### Key Implementations:
1.  **Buffered Audio Queue Proxy (`clap_detector.py`)**:
    *   Subclassed `sr.Microphone` into `BufferedMicSource` to capture the native PyAudio hardware stream, update a `0.5s` rolling buffer, and proxy unmodified chunks into a thread-safe `Queue` so that `SpeechRecognition`'s voice wake word detection and the custom DSP loop share the identical native hardware stream without stealing frames or blocking.
2.  **DSP Clap Classifier (`ClapClassifier`)**:
    *   Constructed a dynamic-rate mathematical analyzer checking for fast Attack/Rise time ($\le 50$ms), rapid Decay ratio ($\le 0.6$), high SNR ($\ge 2.0$), and Zero Crossing Rate (ZCR).
3.  **Laptop Microphone Acoustic Optimization**:
    *   *Issue*: Built-in laptop microphones apply low-pass filtering and software gain control, smoothing out high frequencies and reducing the zero crossing rate of real physical claps down to `0.015` – `0.027`.
    *   *Fix*: Lowered the minimum ZCR threshold (`CLAP_MIN_ZCR`) from `0.05` to `0.01` and peak amplitude (`CLAP_MIN_PEAK_AMP`) to `40`, enabling reliable detection of quiet claps while continuing to ignore speech.
4.  **Hardware Connection click/pop Suppression**:
    *   *Issue*: Opening the audio stream creates a high-amplitude transient click pop. Since the rolling buffer was initialized with zeros, the click pop was evaluated as having infinite SNR, causing immediate false wake-ups on startup.
    *   *Fix*: Added a 1.0-second startup suppression window. All audio chunks captured during the first second are rolled out and ignored, letting the buffer fill with real background noise.
5.  **OS Device Release Delay**:
    *   *Issue*: Closing the calibration microphone stream and opening the passive radar stream in rapid succession caused Windows drivers to fail, returning all zeros.
    *   *Fix*: Introduced a `time.sleep(1.0)` delay in `main.py` right after closing calibration, allowing the OS to fully release the hardware device.
6.  **Concurrency Deadlock Resolution**:
    *   *Issue*: Stopping `listen_in_background` with `wait_for_stop=True` on wake-up caused a complete deadlock. The listener thread was blocked on the empty queue (`self.audio_queue.get()`) while the stopping thread was waiting for the listener to join, locking the audio device.
    *   *Fix*: Built `stop_passive_radar_cleanly` in `main.py`. It injects a silent audio chunk into `radar_mic.audio_queue` to instantly unblock the queue reader, allowing the listener thread to exit cleanly and release PyAudio resources before starting active voice command listening.

### 📊 Verification & Test Logs (Phase 13)
Verified both voice wake ("Wake up") and physical hand claps in live testing:
*   **Startup Verification**: System boots into Standby showing "Say 'Wake up'" without false-triggering.
*   **Speech Detection**: Voice wake successfully transcribes speech and awakens Smaran.
*   **Clap Detection**: Hand claps successfully break through the relaxed ZCR/SNR boundaries and trigger `[WAKE] Clap detected.` logs, immediately playing the welcome chime and starting active speech commands without any locks or freezes.

---

## 🔍 Phase 14: Google Search Grounded Reasoning Mode & Fallback Routing

To enable real-time factual correctness and web search grounding, we integrated Google Gemini 2.5 Flash as the primary reasoning engine, coupled with a robust multi-layered fallback strategy.

### Key Implementations:
1. **Conversational Search Grounding (`gemini_agent.py`)**:
   * Implemented `query_with_history(self, user_text: str, history: list) -> str` in `GeminiAgent`.
   * Maps Smaran's standard history format `[{"role": "user"/"assistant", "content": "..."}]` into the Google GenAI SDK's `Content` schemas `[{"role": "user"/"model", "parts": [{"text": "..."}]}]`.
   * Initializes a chat session with history using `client.chats.create` with search-grounding config (`google_search=types.GoogleSearch()`).
2. **Multi-Layered Cognitive Fallback (`main.py`)**:
   * **Intelligence Mode Routing**: Restructured `_run_intelligence_query` to attempt search-grounded Gemini routing first for general questions. If Gemini encounters errors, rate limits, or missing keys, the query automatically falls back to Groq's llama3 model.
   * **Automation Mode Reasoning**: Restructured `action == "grok_query"` to try `GeminiAgent.ask` first for real-time search-grounded answering. If Gemini is unavailable, it uses the Groq/Wikipedia fallback chain.
3. **Weather Agent Routing & Entity Extraction**:
   * Removed `"weather_scanner"` from `OS_ACTIONS` in `main.py` when in Intelligence Mode. This ensures weather queries are routed through `_run_intelligence_query` to the dynamic `WeatherAgent` instead of bypassing the reasoning layer and going to the local automation weather systems.
   * Expanded `fillers` in `_clean_extracted_entity` to include `"weather"`, `"summary"`, `"summarize"`, `"forecast"`, `"info"`, and `"information"`. This resolves geocoding failures by ensuring that queries like `"give me the weather summary of bengaluru"` extract the clean city name `"bengaluru"`.
4. **Typo and Test Suite Cleanups**:
   * Fixed a logical comparison assignment typo in `gemini_agent.py` test block (`gemini == GeminiAgent()`).

### 📊 Verification & Test Logs (Phase 14)
Verified using `test_live_routing.py` and `test_agent_routing.py`:
* **Stateless factual queries**: Successfully answers real-time questions (e.g. capital of France).
* **Multi-turn conversation queries**: Successfully accesses history to answer context-aware questions (e.g., remembering dog names from past turns).
* **Google Search Grounding**: Successfully retrieves and speaks real-time events (e.g., 2026 T20 World Cup results) without citation bracket or markdown URL artifacts.
* **Fallback routing**: Gracefully falls back to Groq when the Gemini API key is removed/missing or when Gemini's daily quota is exhausted (429 rate limits).
* **Weather Agent Routing**: Verified that weather queries in Intelligence Mode are correctly routed to the detailed `WeatherAgent`, and that clean city extraction succeeds for query patterns containing "summary of".

