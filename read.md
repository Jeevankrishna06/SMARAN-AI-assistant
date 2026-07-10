# Smaran AI Assistant - Capabilities & Documentation

Smaran is a premium, lightweight, highly interactive, and polite voice-enabled AI assistant styled with a British cadence (addressing the user as "sir" or "ma'am"). Smaran is designed to run efficiently on Windows and execute advanced system automation, media management, and logical tasks.

---

## 1. Visual Personality & UI States
Smaran is represented visually by a lightweight Tkinter-based interface featuring a **Chibi Panda** avatar (`smaran_face.jpeg`). The interface includes a voice-responsive state system:

*   **Idle State (`"idle"`)**: Smaran is ready. The avatar runs a smooth, breathing animation, scaling between 99% and 101% of its base size at 30 FPS. The status text reads `"Ready..."`.
*   **Listening State (`"listening"`)**: Triggered when active microphone scanning starts. The panda scales up by 8% to signal active attention. The status text reads `"Listening..."`.
*   **Thinking State (`"thinking"`)**: Triggered after capturing user speech input while processing intents. Runs a cycling dot animation (`Thinking.`, `Thinking..`, `Thinking...`).
*   **Executing State (`"executing"`)**: Displays a task-specific description in the visual console (e.g. `"Calculating countdown..."`, `"Opening YouTube for 'Rolling in the Deep'..."`).
*   **Success Indicator (`"success"`)**: Displays green status feedback for 1.5 seconds upon successful task execution.
*   **Error Indicator (`"error"`)**: Displays red status feedback for 2.5 seconds if an action fails.
*   **Graceful Emoji Fallback**: If the panda face image is missing, the GUI replaces it with a `🐼` unicode emoji and dynamically animates its font size instead, ensuring a beautiful fallback.
*   **Aesthetic & Thread-Safe UI**: Uses a fixed-size avatar frame to completely prevent surrounding widgets from shifting or jittering. The pipeline runs asynchronously to prevent GUI freezes during text-to-speech synthesis.

---

## 2. Voice Options & Audio Indicators

### Male & Female Voice Gender Controls
*   **Voice Toggle Selection**: The GUI includes styled dark-themed `"Male Voice"` and `"Female Voice"` radio options.
*   **Indian English Focus**: Prioritizes Indian English SAPI5 voices (e.g., Microsoft Ravi/Heera/Neerja/Veena) for both male and female genders, falling back to standard English system voices if they are not installed.
*   **Dynamic addressing ("mam")**: Selecting the `"Female Voice"` option automatically translates all verbal prompts and console logs from addressing the user as `"sir"` to `"mam"` (e.g., `"I have been activated, mam."`).

### Wake & Sleep Sound Cues
*   **Soothing Wake Chime**: Prioritizes `Windows Unlock.wav` (a quick, uplifting 1-second chime with no trailing silence) to notify that Smaran is online, falling back to `Windows Logon.wav` or `Windows Background.wav`.
*   **Synchronous Execution**: Played synchronously on background threads to ensure the chime plays completely and never gets cut off, while keeping the GUI fully active and intact.
*   **Shutdown Sleep Chime**: Plays the exact same sound path resolved during startup when going to sleep/shutting down (e.g. `"go to sleep"`, `"exit"`).
*   **Listening Sound Cue**: Plays a brief tone (1800Hz for 120ms) when active microphone listening begins.

---

## 3. Conversational Pattern Recognition

Smaran features advanced local pattern matching to handle conversational interactions:
*   **Status/Well-being Queries**: Words containing `"how are you"` or `"how are you doing"` trigger a polite response: `"I am operating at peak efficiency, sir. Thank you for asking. How can I assist you today?"`
*   **Identity & Naming**: Phrasings like `"whats ur name"`, `"who are you"`, or `"what do people call you"` trigger a self-introduction: `"I am Smaran, your home automation and computing assistant. At your service, sir."`
*   **Creator Recognition**: Queries asking `"who created you"`, `"who created u"`, `"who made you"`, `"who made u"`, `"who developed you"`, or `"who developed u"` correctly respond with the exact predefined credit: `"i was created by my owner jeevan krishna"`

---

## 4. Environmental Awareness Skills

### Skill 1: Weather Scanner
*   **Voice Directives**: `"tell me the weather forecast"`, `"what's the weather"`, etc.
*   **Logic**: Fetches Bengaluru's current weather metrics from `https://wttr.in/Bengaluru?format=%t+%C`.
*   **Offline Fallback**: Catches network exceptions and replies with a polite backup message stating the local weather station is temporarily unreachable.

### Skill 8: Briefing Aggregator
*   **Voice Directives**: `"briefing"`, `"brief me"`, `"give me a brief"`, `"give me a briefing"`, etc.
*   **Logic**: Greets the user dynamically based on the current hour (e.g., "Good morning", "Good afternoon", "Good evening"). Consolidates the current day of the week, full calendar date, 12-hour clock, Bengaluru weather status, and the laptop's physical battery capacity.
*   **Hardware Integration**: Accesses the Win32 `GetSystemPowerStatus` API using Python's `ctypes` library. Safely falls back to `"Wall Power Connected"` on desktop systems.

---

## 5. Multi-Browser & Workspace Launcher Utilities

### Browser Routing & Default Override
*   Smaran scans standard local paths on the system to route commands to the user's preferred browser:
    *   **Google Chrome** (Default browser fallback)
    *   **Microsoft Edge**
    *   **Brave Browser**
    *   **Mozilla Firefox**
    *   **Opera**
    *   **Opera GX** (Scans Local AppData paths to locate `Programs\Opera GX\launcher.exe`)
*   If the requested browser is not installed, it falls back to launching the system's default browser.

### Skill 2: Ecosystem Workspace Launcher
*   **Voice Directives**: `"open gemini and chatgpt workspace in chrome"`, `"launch claude, grok and gemini workspaces"`, etc.
*   **Logic**: Automatically parses the names of requested developer spaces (`"gemini"`, `"chatgpt"`, `"claude"`, `"grok"`) and opens them sequentially in isolated tabs.
*   **Safety**: Spawns tabs asynchronously on a daemon thread with a 0.5s sleep to prevent the UI thread from freezing.

### Skill 7: Smart Google Search
*   **Voice Directives**: `"search for python tutorial in edge"`, `"google how to build a search engine"`, etc.
*   **Logic**: Strips browser prepositions, target names, and search meta-phrases (like `"search for"`, `"google"`, `"look up from google"`) to extract a clean query, then executes a sanitized search replacing spaces with `+` signs.

---

## 6. Media & YouTube Autoplay Integration

### YouTube Autoplay Resolver
*   **Voice Directives**: `"play despacito in brave"`, `"play kunj bihari on youtube in browser"`, etc.
*   **Logic**: Issues an unauthenticated search query to YouTube behind the scenes, scrapes the HTML to resolve the video ID of the top match, and launches the direct autoplay watch link `https://www.youtube.com/watch?v=video_id` in the requested browser.

### Skill 4: YouTube Music Director
*   **Voice Directives**: `"play rolling in the deep on youtube music"`, `"open youtube music"`, etc.
*   **Logic**: Resolves the song query to its video ID and loads the song inside YouTube Music's watch player (`https://music.youtube.com/watch?v=video_id`) to autoplay music immediately. If no query is provided, it opens the main dashboard.

---

## 7. Algorithmic Logic Engines

### Skill 3: Flexible Random Value Generator
*   **Voice Directives**: `"generate a number between 5 and 25"`, `"pick a number between 10 and 50"`, `"choose a value between 1 and 100"`, etc.
*   **Logic**: Parses upper and lower bounds flexibly. Validates constraints and refuses to calculate if `min > max` (e.g. `"I cannot generate a random value because the minimum bound is greater than the maximum bound, sir."`).

### Skill 5: Non-Repeating Wisdom Vault
*   **Voice Directives**: `"tell me a stoic quote"`, `"give me some love wisdom"`, `"retrieve a history quote"`, etc.
*   **Logic**: Hosts **130 curated quotes** with authors across **13 distinct genres**:
    1.  `courage`
    2.  `freedom`
    3.  `romance`
    4.  `history`
    5.  `grit`
    6.  `confidence`
    7.  `love`
    8.  `self-improvement`
    9.  `time-management`
    10. `health`
    11. `spiritual`
    12. `mental health`
    13. `motivation`
*   **No-Repeat History Buffer**: Tracks the last 15 served quotes globally in a queue to guarantee Smaran never tells the same quote consecutively.

### Skill 6: Destination Countdown Timer
*   **Voice Directives**: `"countdown to 6:30 PM"`, `"time remaining until 12 AM"`, `"countdown to 15:30"`, etc.
*   **Logic**: Parses target times in 12-hour AM/PM formats (`H:MM AM/PM` or `H AM/PM`) as well as 24-hour formats. Converts parameters to 24-hour integers and calculates the exact duration.
*   **Constraint Math**: Automatically applies a `+24h` timedelta offset if the target time is earlier than the current system time, preventing negative durations.

---

## 8. Lifecycle Commands & Hardware Controls

### Hardware Controls
*   **Voice Directives**: `"volume up"`, `"volume down"`, `"mute"`.
*   **Logic**: Uses PyAutoGUI to simulate native hardware media keys to control volume levels and mute channels.

### Sleep/Shutdown Operations
*   **Voice Directives**: `"go to sleep"`, `"goodnight"`, `"stop"`, `"exit"`, `"turn off"`.
*   **Logic**: Plays a polite exit speech (`"Goodbye, sir. Shutting down systems now."`) and terminates the assistant process cleanly.
