import os
import subprocess
import webbrowser
import sys
import time
import pyautogui
import ctypes

class OSController:
    def __init__(self):
        # Detect the operating system (Windows, Darwin/Mac, Linux)
        self.platform = sys.platform
        self.quote_history = []
        print(f"[INIT] OS Controller activated for platform: {self.platform}")

    def execute_command(self, brain_command):
        """
        Takes the JSON dictionary from the brain and maps it to OS actions.
        """
        action = brain_command.get("action")
        target = brain_command.get("target", "").lower()
        parameter = brain_command.get("parameter", "")

        print(f"\n[EXECUTING TASK] Action: {action} | Target: {target}")

        if action == "launch_app":
            return self.launch_application(target, parameter)
        elif action == "system_control":
            return self.control_system(target, parameter)
        elif action == "conversational_reply":
            return True, "Handled via chat."
        elif action == "calculator_compute":
            return self.compute_and_show_in_calculator(parameter)
        elif action == "weather_scanner":
            return self.scan_weather()
        elif action == "morning_briefing":
            return self.morning_briefing()
        elif action == "ecosystem_workspace":
            return self.launch_ecosystem_workspace(target, parameter)
        elif action == "youtube_music":
            return self.launch_youtube_music(target, parameter)
        elif action == "random_generator":
            return self.generate_random_value(parameter)
        elif action == "wisdom_vault":
            return self.retrieve_wisdom(parameter)
        elif action == "countdown_timer":
            return self.countdown_timer(parameter)
        elif action == "study_mode":
            return self.activate_study_mode()
        elif action == "developer_mode":
            return self.activate_developer_mode()
        elif action == "fun_mode":
            return self.activate_fun_mode()
        elif action == "deep_mode":
            return self.activate_deep_mode()
        elif action == "set_clock_timer":
            return self.open_clock()
        elif action == "activate_vision":
            return self.activate_vision_mode()
        elif action == "deactivate_vision":
            return self.deactivate_vision_mode()
        else:
            return False, f"Unknown action type: {action}"

    def _get_browser_path(self, browser_name):
        # Common executables and their installation subpaths on Windows
        browser_info = {
            "chrome": {
                "paths": [
                    os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "Google", "Chrome", "Application", "chrome.exe"),
                    os.path.join(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"), "Google", "Chrome", "Application", "chrome.exe"),
                    os.path.join(os.environ.get("LocalAppData", ""), "Google", "Chrome", "Application", "chrome.exe")
                ]
            },
            "msedge": {
                "paths": [
                    os.path.join(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"), "Microsoft", "Edge", "Application", "msedge.exe"),
                    os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "Microsoft", "Edge", "Application", "msedge.exe")
                ]
            },
            "brave": {
                "paths": [
                    os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "BraveSoftware", "Brave-Browser", "Application", "brave.exe"),
                    os.path.join(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"), "BraveSoftware", "Brave-Browser", "Application", "brave.exe"),
                    os.path.join(os.environ.get("LocalAppData", ""), "BraveSoftware", "Brave-Browser", "Application", "brave.exe")
                ]
            },
            "firefox": {
                "paths": [
                    os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "Mozilla Firefox", "firefox.exe"),
                    os.path.join(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"), "Mozilla Firefox", "firefox.exe")
                ]
            },
            "opera": {
                "paths": [
                    os.path.join(os.environ.get("LocalAppData", ""), "Programs", "Opera", "launcher.exe"),
                    os.path.join(os.environ.get("LocalAppData", ""), "Programs", "Opera", "opera.exe"),
                    os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "Opera", "launcher.exe"),
                    os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "Opera", "opera.exe"),
                    os.path.join(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"), "Opera", "launcher.exe"),
                    os.path.join(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"), "Opera", "opera.exe")
                ]
            },
            "operagx": {
                "paths": [
                    os.path.join(os.environ.get("LocalAppData", ""), "Programs", "Opera GX", "launcher.exe"),
                    os.path.join(os.environ.get("LocalAppData", ""), "Programs", "Opera GX", "opera.exe"),
                    os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "Opera GX", "launcher.exe"),
                    os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "Opera GX", "opera.exe"),
                    os.path.join(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"), "Opera GX", "launcher.exe"),
                    os.path.join(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"), "Opera GX", "opera.exe")
                ]
            },
            "opera gx": {
                "paths": [
                    os.path.join(os.environ.get("LocalAppData", ""), "Programs", "Opera GX", "launcher.exe"),
                    os.path.join(os.environ.get("LocalAppData", ""), "Programs", "Opera GX", "opera.exe"),
                    os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "Opera GX", "launcher.exe"),
                    os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "Opera GX", "opera.exe"),
                    os.path.join(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"), "Opera GX", "launcher.exe"),
                    os.path.join(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"), "Opera GX", "opera.exe")
                ]
            }
        }
        
        info = browser_info.get(browser_name)
        if not info:
            return None
            
        for p in info["paths"]:
            if p and os.path.exists(p):
                return p
        return None

    def _get_chrome_path(self):
        return self._get_browser_path("chrome")

    # ─────────────────────────────────────────────────────────────────────────
    # CALCULATOR COMPUTE ENGINE
    # ─────────────────────────────────────────────────────────────────────────

    def _normalize_math_expression(self, text):
        """
        Converts natural language math phrasing to a standard expression string.
        e.g. '100 times 2' -> '100*2', '50 divided by 5' -> '50/5'
        Supports integers, decimals, repeated operations, scientific functions,
        and common spoken operators.
        """
        import re
        expr = text.lower().strip()
        expr = re.sub(r'[?,]', ' ', expr)

        number_words = {
            "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4",
            "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9",
            "ten": "10",
        }
        for word, value in number_words.items():
            expr = re.sub(rf'\b{word}\b', value, expr)

        # Remove noise phrases (longest first to avoid partial matches)
        noise_phrases = [
            "in the calculator", "in calculator", "on the calculator",
            "the result of", "result of", "the answer to",
            "what is", "what's", "please",
            "calculate", "compute", "solve", "find", "evaluate",
        ]
        for phrase in noise_phrases:
            expr = expr.replace(phrase, " ")

        # "sum of 8 plus 2" is a request wrapper, not a leading plus operator.
        expr = re.sub(r'^\s*(the\s+)?sum\s+of\s+', ' ', expr)

        # Word -> function name conversions (longest patterns first)
        expr = re.sub(r'\bnatural\s+log\s+of\s+([\d\+\-\*\/\.\(\)\s\w]+)', r'log(\1)', expr)
        expr = re.sub(r'\bln\s+of\s+([\d\+\-\*\/\.\(\)\s\w]+)', r'log(\1)', expr)
        expr = re.sub(r'\blog\s+base\s+10\s+of\s+([\d\+\-\*\/\.\(\)\s\w]+)', r'log10(\1)', expr)
        expr = re.sub(r'\blog\s+of\s+([\d\+\-\*\/\.\(\)\s\w]+)', r'log10(\1)', expr)
        expr = re.sub(r'\blog\s+([\d\+\-\*\/\.\(\)\s\w]+)', r'log10(\1)', expr)
        
        expr = re.sub(r'\b(?:square\s+)?root\s+of\s+([\d\+\-\*\/\.\(\)\s\w]+)', r'sqrt(\1)', expr)
        expr = re.sub(r'\bsqrt\s+of\s+([\d\+\-\*\/\.\(\)\s\w]+)', r'sqrt(\1)', expr)
        expr = re.sub(r'\bsqrt\s+([\d\+\-\*\/\.\(\)\s\w]+)', r'sqrt(\1)', expr)
        
        expr = re.sub(r'\bsquare\s+of\s+([\d\+\-\*\/\.\(\)\s\w]+)', r'(\1)**2', expr)
        expr = re.sub(r'\bsquare\s+([\d\+\-\*\/\.\(\)\s\w]+)', r'(\1)**2', expr)
        expr = re.sub(r'\bcube\s+of\s+([\d\+\-\*\/\.\(\)\s\w]+)', r'(\1)**3', expr)
        
        expr = re.sub(r'\bexponential\s+of\s+([\d\+\-\*\/\.\(\)\s\w]+)', r'exp(\1)', expr)
        expr = re.sub(r'\bexponential\s+([\d\+\-\*\/\.\(\)\s\w]+)', r'exp(\1)', expr)
        expr = re.sub(r'\bexp\s+of\s+([\d\+\-\*\/\.\(\)\s\w]+)', r'exp(\1)', expr)
        expr = re.sub(r'\be\s+to\s+the\s+power\s+of\s+([\d\+\-\*\/\.\(\)\s\w]+)', r'exp(\1)', expr)
        expr = re.sub(r'\be\s+raised\s+to\s+([\d\+\-\*\/\.\(\)\s\w]+)', r'exp(\1)', expr)
        
        expr = re.sub(r'\bsine?\s+of\s+([\d\+\-\*\/\.\(\)\s\w]+)', r'sin(\1)', expr)
        expr = re.sub(r'\bsin\s+of\s+([\d\+\-\*\/\.\(\)\s\w]+)', r'sin(\1)', expr)
        expr = re.sub(r'\bsin\s+([\d\+\-\*\/\.\(\)\s\w]+)', r'sin(\1)', expr)
        expr = re.sub(r'\bcos\s+of\s+([\d\+\-\*\/\.\(\)\s\w]+)', r'cos(\1)', expr)
        expr = re.sub(r'\bcosine?\s+of\s+([\d\+\-\*\/\.\(\)\s\w]+)', r'cos(\1)', expr)
        expr = re.sub(r'\bcos\s+([\d\+\-\*\/\.\(\)\s\w]+)', r'cos(\1)', expr)
        expr = re.sub(r'\btan\s+of\s+([\d\+\-\*\/\.\(\)\s\w]+)', r'tan(\1)', expr)
        expr = re.sub(r'\btangente?\s+of\s+([\d\+\-\*\/\.\(\)\s\w]+)', r'tan(\1)', expr)
        expr = re.sub(r'\btan\s+([\d\+\-\*\/\.\(\)\s\w]+)', r'tan(\1)', expr)
        expr = re.sub(r'\babs(?:olute)?\s+(?:value\s+)?of\s+([\d\+\-\*\/\.\(\)\s\w]+)', r'abs(\1)', expr)

        # Word -> operator substitutions (longest patterns first to avoid partial matches)
        word_ops = [
            # Power operations
            (r'\bto the power of\b',  '**'),
            (r'\bto the power\b',     '**'),
            (r'\bpowered by\b',       '**'),
            (r'\bsquared\b',          '**2'),
            (r'\bcubed\b',            '**3'),
            # Multiplication (all variants)
            (r'\bmultiplied by\b',    '*'),
            (r'\bmultiply by\b',      '*'),
            (r'\bmultiply\b',         '*'),
            (r'\btimes\b',            '*'),
            (r'\binto\b',             '*'),
            (r'\bstar\b',             '*'),
            # Division (all variants)
            (r'\bdivided by\b',       '/'),
            (r'\bdivide by\b',        '/'),
            (r'\bdivide\b',           '/'),
            (r'\bby\b',               '/'),  # Must come after compound phrases
            (r'\bover\b',             '/'),
            # Addition (all variants)
            (r'\badded to\b',         '+'),
            (r'\badd\b',              '+'),
            (r'\bsum\b',              '+'),
            (r'\bplus\b',             '+'),
            # Subtraction (all variants)
            (r'\bsubtracted from\b',  '-'),
            (r'\bsubtract\b',         '-'),
            (r'\bminus\b',            '-'),
            (r'\btake away\b',        '-'),
            # Misc
            (r'(\d)\s*x\s*(\d)',      r'\1*\2'),
            (r'\bpi\b',               'pi'),
            (r'\bconstant e\b',       'e'),
            (r'\bpoint\b',            '.'),
            (r'\bof\b',               ''),
            (r'\bthe\b',              ''),
            (r'\ba\b',                ''),
            (r'\ban\b',               ''),
        ]
        for pattern, replacement in word_ops:
            expr = re.sub(pattern, replacement, expr)

        # Strip everything that is not a valid math alphanumeric character
        expr = re.sub(r'[^\d\+\-\*\/\.\(\)\s\w]', '', expr)
        # Collapse multiple spaces and format cleanly
        expr = re.sub(r'\s+', ' ', expr).strip()
        expr = re.sub(r'\s*([\+\-\*\/\(\)])\s*', r'\1', expr)
        # Whisper often hears "8.30" as "8 30"; keep that as a decimal.
        expr = re.sub(r'\b(\d+)\s+(\d{1,3})\b', r'\1.\2', expr)
        expr = re.sub(r'(?<=\d)\s+(?=\d)', '', expr)
        return expr

    def _safe_eval(self, expr):
        """
        Safely evaluates a mathematical expression string.
        Returns (result, clean_expr) tuple.
        """
        import re
        import math
        
        # Dict of allowed math functions/constants
        SAFE_DICT = {
            "sqrt": math.sqrt,
            "log": math.log,
            "log10": math.log10,
            "ln": math.log,
            "exp": math.exp,
            "sin": math.sin,
            "cos": math.cos,
            "tan": math.tan,
            "pi": math.pi,
            "e": math.e,
            "pow": pow,
            "abs": abs
        }

        # Check safety: verify that the expression only contains numbers, operators, parens, and allowed math words
        test_str = expr.lower()
        for name in SAFE_DICT.keys():
            test_str = re.sub(r'\b' + name + r'\b', '', test_str)
            
        # Strip allowed characters: digits, operators, parens, spaces
        unsafe_check = re.sub(r'[\d\+\-\*\/\.\(\)\s]', '', test_str)
        if unsafe_check:
            raise ValueError(f"Unsafe math expression contains disallowed characters: '{unsafe_check}'")
            
        # Clean expression is evaluated in a restricted environment
        result = eval(expr, {"__builtins__": None}, SAFE_DICT)  # noqa: S307  safe: sandbox check above
        
        # Format the result nicely
        if isinstance(result, float) and result == int(result):
            return int(result), expr
        elif isinstance(result, float):
            return round(result, 8), expr
        return result, expr

    def _type_in_calculator(self, clean_expr, result):
        """
        Types the math expression into the focused Windows Calculator.
        For scientific expressions with letters, it types the evaluated result directly.
        For simple equations, it types key-by-key and presses Enter.
        """
        try:
            time.sleep(0.4)
            pyautogui.press('escape')   # Clear any pre-existing input
            time.sleep(0.15)
            
            # Check if there are alphabetical characters in clean_expr
            has_letters = any(c.isalpha() for c in clean_expr)
            
            if has_letters:
                # Type the final result directly
                for char in str(result):
                    pyautogui.press(char)
                    time.sleep(0.05)
            else:
                for char in clean_expr:
                    if char.isdigit():
                        pyautogui.press(char)
                    elif char == '+':
                        pyautogui.press('+')
                    elif char == '-':
                        pyautogui.press('-')
                    elif char == '*':
                        pyautogui.hotkey('shift', '8')
                    elif char == '/':
                        pyautogui.press('/')
                    elif char == '.':
                        pyautogui.press('.')
                    elif char == '(':
                        pyautogui.hotkey('shift', '9')
                    elif char == ')':
                        pyautogui.hotkey('shift', '0')
                    time.sleep(0.05)
                pyautogui.press('enter')
        except Exception as e:
            print(f"[CALC TYPE ERROR] {e}")

    def _type_in_notepad(self, text):
        """
        Pastes text into the focused Notepad window using the clipboard
        (win32clipboard + Ctrl+V). Clipboard-based paste is the most reliable
        method for arbitrary Unicode text including spaces and punctuation.
        Falls back to pyautogui.typewrite() if win32clipboard is unavailable.
        """
        try:
            time.sleep(0.4)
            try:
                import win32clipboard
                win32clipboard.OpenClipboard()
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardText(text, win32clipboard.CF_UNICODETEXT)
                win32clipboard.CloseClipboard()
                time.sleep(0.2)
                pyautogui.hotkey('ctrl', 'v')
            except ImportError:
                # Fallback: character-by-character (slower, ASCII only)
                pyautogui.typewrite(text, interval=0.05)
        except Exception as e:
            print(f"[NOTEPAD TYPE ERROR] {e}")

    def compute_and_show_in_calculator(self, expression_text):
        """
        Full calculator compute pipeline:
        1. Normalise spoken math to symbols ('times' -> '*', etc.)
        2. Safely evaluate the expression with Python
        3. Open Windows Calculator
        4. Wait for it to load
        5. Type the expression or result and press Enter
        6. Return the spoken result string
        """
        try:
            normalized = self._normalize_math_expression(expression_text)
            print(f"[CALC] Normalized: '{expression_text}' -> '{normalized}'")
            result, clean_expr = self._safe_eval(normalized)
            print(f"[CALC] Evaluated: '{clean_expr}' = {result}")

            # Open Windows Calculator
            subprocess.Popen("calc.exe", shell=True)
            time.sleep(2.0)     # Wait for UWP Calculator to fully load and get focus

            # Type the expression into the Calculator window
            self._type_in_calculator(clean_expr, result)

            return True, f"The result of {expression_text} is {result}, boss." 

        except Exception as e:
            print(f"[CALC COMPUTE ERROR] {e}")
            # Graceful fallback: still open Calculator even if compute failed
            try:
                subprocess.Popen("calc.exe", shell=True)
            except Exception:
                pass
            return True, "Opened Calculator, boss. Could not automatically compute the expression."

    # ─────────────────────────────────────────────────────────────────────────
    # NOTEPAD TYPING
    # ─────────────────────────────────────────────────────────────────────────
    def _get_first_youtube_video(self, song_name):
        try:
            import requests
            import re
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            url = f"https://www.youtube.com/results?search_query={song_name.replace(' ', '+')}"
            r = requests.get(url, headers=headers, timeout=5)
            if r.status_code == 200:
                matches = re.findall(r'/watch\?v=([a-zA-Z0-9_-]{11})', r.text)
                if matches:
                    return f"https://www.youtube.com/watch?v={matches[0]}"
        except Exception as e:
            print(f"⚠️ [YT RESOLVER] Error fetching video: {e}")
        return None

    def launch_application(self, app_name, parameter=""):
        """Launches native applications or opens URLs in a browser"""
        try:
            # Check if targeted app is a known web browser
            browsers = ["browser", "chrome", "msedge", "firefox", "opera", "brave", "safari", "operagx", "opera gx"]
            is_browser = app_name in browsers

            # Normalize app name
            normalized_app = "msedge" if app_name == "edge" else app_name

            native_apps = {"notepad", "notes", "calculator", "calc", "cmd", "explorer", "fileexplorer", "file explorer", "task manager"}
            is_native = app_name in native_apps

            if is_browser or (parameter and parameter != "none" and not is_native):
                # Construct query or navigation URL
                url = "https://www.google.com"
                if parameter and parameter != "none":
                    if parameter.startswith("http://") or parameter.startswith("https://"):
                        url = parameter
                    elif parameter.startswith("youtube "):
                        song_name = parameter[len("youtube "):]
                        # Resolve first watch URL dynamically to autoplay video directly
                        video_url = self._get_first_youtube_video(song_name)
                        if video_url:
                            url = f"{video_url}&autoplay=1"
                        else:
                            url = f"https://www.youtube.com/results?search_query={song_name.replace(' ', '+')}"
                    else:
                        url = f"https://www.google.com/search?q={parameter.replace(' ', '+')}"

                # Determine target browser. Default generic "browser" to "chrome"
                target_browser = "chrome" if normalized_app == "browser" else normalized_app

                if target_browser in ["chrome", "msedge", "firefox", "opera", "brave", "operagx", "opera gx"]:
                    if self.platform.startswith("win"):
                        browser_path = self._get_browser_path(target_browser)
                        if browser_path:
                            autoplay_flag = " --autoplay-policy=no-user-gesture-required" if "autoplay=1" in url else ""
                            cmd = f'"{browser_path}"{autoplay_flag} "{url}"'
                            subprocess.Popen(cmd, shell=True)
                            return True, f"Opened {target_browser.capitalize()} and navigated to URL."
                        else:
                            # Browser not found, fallback to default browser
                            webbrowser.open(url)
                            return True, f"{target_browser.capitalize()} not installed. Opened default browser."

                # Otherwise open in user's default system browser
                webbrowser.open(url)
                return True, "Opened default browser."

            # Case 2: Windows Native Apps
            if self.platform.startswith("win"):
                # ── NOTEPAD WITH TYPING ─────────────────────────────────────────────
                # Intercept when brain sends parameter="type:MESSAGE"
                if app_name in ["notepad", "notes"] and parameter.startswith("type:"):
                    text_to_type = parameter[5:].strip()
                    subprocess.Popen("notepad.exe", shell=True)
                    time.sleep(2.0)     # Wait for Notepad to fully load and get focus
                    self._type_in_notepad(text_to_type)
                    return True, f"Opened Notepad and typed your message, boss."

                common_apps = {
                    "notepad":        "notepad.exe",
                    "calculator":     "calc.exe",
                    "calc":           "calc.exe",
                    "cmd":            "cmd.exe",
                    "explorer":       "explorer.exe",
                    "fileexplorer":   "explorer.exe",
                    "file explorer":  "explorer.exe",
                    "task manager":   "taskmgr.exe",
                    # UWP apps launched via ms-protocol URIs
                    "clock":          "start ms-clock:",
                    "alarms":         "start ms-clock:",
                    "timer":          "start ms-clock:timer",
                    "whatsapp":       "start whatsapp:",
                }
                
                cmd = common_apps.get(app_name, app_name)
                # Dispatch: URIs already prefixed with 'start' → run as-is
                # .exe commands → run directly
                # Everything else → let shell resolve via 'start'
                if cmd.startswith("start ") or cmd.startswith("start\t"):
                    subprocess.Popen(cmd, shell=True)
                elif cmd.endswith(".exe"):
                    subprocess.Popen(cmd, shell=True)
                else:
                    subprocess.Popen(f"start {cmd}", shell=True)
                return True, f"Successfully launched {app_name}"

            # Case 3: MacOS Native Apps
            elif self.platform == "darwin":
                # Mac uses the 'open -a' command to launch apps by name
                subprocess.Popen(["open", "-a", app_name])
                return True, f"Successfully launched {app_name} via MacOS"

            # Case 4: Linux Native Apps
            else:
                subprocess.Popen([app_name], shell=True)
                return True, f"Successfully launched {app_name} via Linux"

        except Exception as e:
            return False, f"Failed to launch {app_name}. Error: {str(e)}"

    def control_system(self, setting, value=""):
        """Handles hardware / OS specific tasks like volume, shortcuts, etc."""
        try:
            # Volume Controls using PyAutoGUI media keys (Cross-platform)
            if setting == "volume_up":
                for _ in range(5):  # Turn it up by 5 steps
                    pyautogui.press("volumeup")
                return True, "Increased system volume."
                
            elif setting == "volume_down":
                for _ in range(5):
                    pyautogui.press("volumedown")
                return True, "Decreased system volume."
                
            elif setting == "mute":
                pyautogui.press("volumemute")
                return True, "Toggled system mute."
                
            elif setting == "get_volume":
                try:
                    from pycaw.pycaw import AudioUtilities
                    speakers = AudioUtilities.GetSpeakers()
                    volume = speakers.EndpointVolume
                    current_val = int(round(volume.GetMasterVolumeLevelScalar() * 100))
                    return True, f"Your system volume is currently at {current_val} percent, boss."
                except Exception as ex:
                    print(f"pycaw volume retrieve failed: {ex}")
                    return True, "I am unable to retrieve the exact volume level right now, boss, but you can adjust it using my volume up and down controls."
                
            else:
                return False, f"System control setting '{setting}' not mapped yet."
                
        except Exception as e:
            return False, f"Failed to modify system setting. Error: {str(e)}"

    def scan_weather(self):
        try:
            import requests
            headers = {"User-Agent": "curl/7.68.0"}
            r = requests.get("https://wttr.in/Bengaluru?format=%t+%C", headers=headers, timeout=5)
            if r.status_code == 200:
                weather_data = r.text.strip()
                return True, f"The current weather in Bengaluru is {weather_data}."
        except Exception as e:
            print(f"⚠️ [WEATHER SCANNER ERROR] {e}")
        return True, "The local weather station is temporarily unreachable."

    def _get_battery_status(self):
        if not self.platform.startswith("win"):
            return "Wall Power Connected"
            
        import ctypes
        class SYSTEM_POWER_STATUS(ctypes.Structure):
            _fields_ = [
                ('ACLineStatus', ctypes.c_byte),
                ('BatteryFlag', ctypes.c_byte),
                ('BatteryLifePercent', ctypes.c_byte),
                ('Reserved1', ctypes.c_byte),
                ('BatteryLifeTime', ctypes.c_ulong),
                ('BatteryFullLifeTime', ctypes.c_ulong),
            ]
        
        try:
            status = SYSTEM_POWER_STATUS()
            if ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(status)):
                percent = status.BatteryLifePercent
                if percent == 255 or percent < 0 or percent > 100:
                    return "Wall Power Connected"
                return f"{percent}%"
        except Exception:
            pass
        return "Wall Power Connected"

    def morning_briefing(self):
        import datetime
        now = datetime.datetime.now()
        hour = now.hour
        
        if hour < 12:
            greeting = "Good morning"
        elif hour < 17:
            greeting = "Good afternoon"
        else:
            greeting = "Good evening"
            
        day_of_week = now.strftime("%A")
        date_str = now.strftime("%B %d, %Y")
        time_str = now.strftime("%I:%M %p")
        
        _, weather_msg = self.scan_weather()
        if "weather in Bengaluru is" in weather_msg:
            weather_brief = weather_msg.replace("The current weather", "weather")
        else:
            weather_brief = "the local weather station is temporarily unreachable"
            
        battery_status = self._get_battery_status()
        
        briefing = (
            f"{greeting}, boss. Today is {day_of_week}, {date_str}. "
            f"The time is now {time_str}. As for the climate, {weather_brief}. "
            f"Your current battery status reports: {battery_status}."
        )
        return True, briefing

    def launch_ecosystem_workspace(self, target_browser, parameter):
        workspaces = {
            "gemini": "https://gemini.google.com",
            "chatgpt": "https://chatgpt.com",
            "claude": "https://claude.ai",
            "grok": "https://grok.com",
            "perplexity": "https://www.perplexity.ai"
        }
        
        targets = [t.strip() for t in parameter.split(",") if t.strip()]
        if not targets:
            return False, "No workspace targets specified."
            
        target_browser = "chrome" if target_browser == "browser" else target_browser
        browser_path = self._get_browser_path(target_browser)
        
        import threading
        def spawn_tabs():
            try:
                for t in targets:
                    url = workspaces.get(t)
                    if not url:
                        continue
                    if self.platform.startswith("win") and browser_path:
                        cmd = f'"{browser_path}" "{url}"'
                        subprocess.Popen(cmd, shell=True)
                    else:
                        webbrowser.open(url)
                    import time
                    time.sleep(0.5)
            except Exception as e:
                print(f"Error in workspace launcher: {e}")
                
        threading.Thread(target=spawn_tabs, daemon=True).start()
        return True, f"Sequential launch of workspaces: {', '.join(targets)} initialized."

    def launch_youtube_music(self, target_browser, parameter):
        url = "https://music.youtube.com"
        if parameter and parameter != "none":
            video_url = self._get_first_youtube_video(parameter)
            if video_url:
                import re
                match = re.search(r'v=([a-zA-Z0-9_-]{11})', video_url)
                if match:
                    video_id = match.group(1)
                    url = f"https://music.youtube.com/watch?v={video_id}&autoplay=1"
                else:
                    url = f"https://music.youtube.com/search?q={parameter.replace(' ', '+')}"
            else:
                url = f"https://music.youtube.com/search?q={parameter.replace(' ', '+')}"
            
        target_browser = "chrome" if target_browser == "browser" else target_browser
        browser_path = self._get_browser_path(target_browser)
        
        if self.platform.startswith("win") and browser_path:
            autoplay_flag = " --autoplay-policy=no-user-gesture-required" if "autoplay=1" in url else ""
            cmd = f'"{browser_path}"{autoplay_flag} "{url}"'
            subprocess.Popen(cmd, shell=True)
        else:
            webbrowser.open(url)
            
        return True, f"Navigated to YouTube Music: {url}"

    def generate_random_value(self, parameter):
        try:
            val_a, val_b = map(int, parameter.split(","))
        except Exception:
            return False, "Invalid parameters for random number generator."
            
        if val_a > val_b:
            return True, "I cannot generate a random value because the minimum bound is greater than the maximum bound, boss."
            
        import random
        result = random.randint(val_a, val_b)
        return True, f"Your random number between {val_a} and {val_b} is {result}, boss."

    def retrieve_wisdom(self, parameter):
        vault = {
            "courage": [
                "Courage is not the absence of fear, but rather the assessment that something else is more important than fear. — Franklin D. Roosevelt",
                "I learned that courage was not the absence of fear, but the triumph over it. — Nelson Mandela",
                "Success is not final, failure is not fatal: it is the courage to continue that counts. — Winston Churchill",
                "He who is brave is free. — Seneca",
                "Courage is grace under pressure. — Ernest Hemingway",
                "It takes courage to grow up and become who you really are. — E.E. Cummings",
                "Fortitude is the guard and support of the other virtues. — John Locke",
                "The only thing we have to fear is fear itself. — Franklin D. Roosevelt",
                "You must do the thing you think you cannot do. — Eleanor Roosevelt",
                "Brave is not the person who does not feel afraid, but the one who conquers that fear. — Nelson Mandela"
            ],
            "freedom": [
                "Freedom is not worth having if it does not include the freedom to make mistakes. — Mahatma Gandhi",
                "Those who deny freedom to others deserve it not for themselves. — Abraham Lincoln",
                "No one is more hopelessly enslaved than those who falsely believe they are free. — Johann Wolfgang von Goethe",
                "The only way to deal with an unfree world is to become so absolutely free that your very existence is an act of rebellion. — Albert Camus",
                "For to be free is not merely to cast off one's chains, but to live in a way that respects and enhances the freedom of others. — Nelson Mandela",
                "Man is free at the moment he wishes to be. — Voltaire",
                "Freedom lies in being bold. — Robert Frost",
                "Liberty, when it begins to take root, is a plant of rapid growth. — George Washington",
                "True freedom is creative, a positive force that can design a better future. — Dalai Lama",
                "We must be free not because we claim freedom, but because we practice it. — William Faulkner"
            ],
            "romance": [
                "In all the world, there is no heart for me like yours. In all the world, there is no love for you like mine. — Maya Angelou",
                "Whatever our souls are made of, his and mine are the same. — Emily Brontë",
                "We loved with a love that was more than love. — Edgar Allan Poe",
                "You make me want to be a better man. — Melvin Udall",
                "You are my heart, my life, my entire existence. — Julie Kagawa",
                "You pierce my soul. I am half agony, half hope. — Jane Austen",
                "I have loved you in infinite forms, infinite times, in life after life, age after age, forever. — Rabindranath Tagore",
                "If I had a flower for every time I thought of you... I could walk through my garden forever. — Alfred Tennyson",
                "I love you not only for what you are, but for what I am when I am with you. — Elizabeth Barrett Browning",
                "I would rather share one lifetime with you than face all the ages of this world alone. — J.R.R. Tolkien"
            ],
            "history": [
                "Those who cannot remember the past are condemned to repeat it. — George Santayana",
                "History is written by the victors. — Winston Churchill",
                "The more you know about the past, the better prepared you are for the future. — Theodore Roosevelt",
                "History repeats itself, first as tragedy, second as farce. — Karl Marx",
                "History is a pack of lies we play on the dead. — Voltaire",
                "A people without the knowledge of their past history, origin and culture is like a tree without roots. — Marcus Garvey",
                "We are not makers of history. We are made by history. — Martin Luther King Jr.",
                "History is a guide to navigation in perilous times. — David C. McCullough",
                "The main thing history teaches us is that we do not learn from history. — Georg Wilhelm Friedrich Hegel",
                "To study history is to study the secrets of human behavior. — Confucius"
            ],
            "grit": [
                "Grit is passion and perseverance for very long-term goals. — Angela Duckworth",
                "Grit is having stamina. Grit is sticking with your future, day in, day out. — Angela Duckworth",
                "It's not that I'm so smart, it's just that I stay with problems longer. — Albert Einstein",
                "Fall seven times, stand up eight. — Japanese Proverb",
                "Grit is that extra something that separates the most successful people from the rest. — Travis Bradberry",
                "Persistence guarantees that results are inevitable. — Paramahansa Yogananda",
                "Continuous effort - not strength or intelligence - is the key to unlocking our potential. — Winston Churchill",
                "Strength does not come from physical capacity. It comes from an indomitable will. — Mahatma Gandhi",
                "The difference between a successful person and others is not a lack of strength, not a lack of knowledge, but rather a lack in will. — Vince Lombardi",
                "Perseverance is the hard work you do after you get tired of doing the hard work you already did. — Newt Gingrich"
            ],
            "confidence": [
                "No one can make you feel inferior without your consent. — Eleanor Roosevelt",
                "Believe you can and you're halfway there. — Theodore Roosevelt",
                "With confidence, you have won before you have started. — Marcus Garvey",
                "Self-confidence is the first requisite to great undertakings. — Samuel Johnson",
                "Whether you think you can or think you can't, you're right. — Henry Ford",
                "To be yourself in a world that is constantly trying to make you something else is the greatest accomplishment. — Ralph Waldo Emerson",
                "Kindness in words creates confidence. Kindness in thinking creates profoundness. — Lao Tzu",
                "If you have no confidence in self, you are twice defeated in the race of life. — Marcus Garvey",
                "Confidence comes not from always being right but from not fearing to be wrong. — Peter T. Mcintyre",
                "As soon as you trust yourself, you will know how to live. — Johann Wolfgang von Goethe"
            ],
            "love": [
                "Where there is love there is life. — Mahatma Gandhi",
                "Being deeply loved by someone gives you strength, while loving someone deeply gives you courage. — Lao Tzu",
                "Love is composed of a single soul inhabiting two bodies. — Aristotle",
                "Let us always meet each other with smile, for the smile is the beginning of love. — Mother Teresa",
                "The greatest happiness of life is the conviction that we are loved. — Victor Hugo",
                "Love recognizes no barriers. It jumps hurdles, leaps fences, penetrates walls to arrive at its destination full of hope. — Maya Angelou",
                "The best thing to hold onto in life is each other. — Audrey Hepburn",
                "There is only one happiness in this life, to love and be loved. — George Sand",
                "We are shaped and fashioned by what we love. — Johann Wolfgang von Goethe",
                "Love is the only force capable of transforming an enemy into a friend. — Martin Luther King Jr."
            ],
            "self-improvement": [
                "The only person you should try to be better than is the person you were yesterday. — Anonymous",
                "Become the change you want to see in the world. — Mahatma Gandhi",
                "Every day, in every way, I am getting better and better. — Émile Coué",
                "There is nothing noble in being superior to your fellow man; true nobility is being superior to your former self. — Ernest Hemingway",
                "The key to growth is the introduction of higher dimensions of consciousness into our awareness. — Lao Tzu",
                "Set a goal so big that you can't achieve it until you grow into the person who can. — Unknown",
                "Do the best you can until you know better. Then when you know better, do better. — Maya Angelou",
                "We are what we repeatedly do. Excellence, then, is not an act, but a habit. — Aristotle",
                "The capacity to learn is a gift; the ability to learn is a skill; the willingness to learn is a choice. — Brian Herbert",
                "Investing in yourself is the best investment you will ever make. — Robin Sharma"
            ],
            "time-management": [
                "Time is what we want most, but what we use worst. — William Penn",
                "The bad news is time flies. The good news is you're the pilot. — Michael Altshuler",
                "Until you value yourself, you won't value your time. Until you value your time, you will not do anything with it. — M. Scott Peck",
                "He who defines his time, defines his life. — Peter Drucker",
                "Time you enjoy wasting is not wasted time. — Marthe Troly-Curtin",
                "You may delay, but time will not. — Benjamin Franklin",
                "Concentrate all your thoughts upon the work at hand. The sun's rays do not burn until brought to a focus. — Alexander Graham Bell",
                "Never leave that till tomorrow which you can do today. — Benjamin Franklin",
                "Ordinary people think merely of spending time, great people think of using it. — Arthur Schopenhauer",
                "Time is a created thing. To say 'I don't have time' is like saying, 'I don't want to.' — Lao Tzu"
            ],
            "health": [
                "It is health that is real wealth and not pieces of gold and silver. — Mahatma Gandhi",
                "He who has health has hope; and he who has hope has everything. — Arabian Proverb",
                "A fit body, a calm mind, a house full of love. These things cannot be bought - they must be earned. — Naval Ravikant",
                "To keep the body in good health is a duty... otherwise we shall not be able to keep our mind strong and clear. — Buddha",
                "The groundwork of all happiness is health. — Leigh Hunt",
                "Your body holds deep wisdom. Trust in it. Learn from it. — Bella Bleu",
                "Take care of your body. It's the only place you have to live. — Jim Rohn",
                "The wish for healing has always been half of health. — Seneca",
                "Let food be thy medicine and medicine be thy food. — Hippocrates",
                "Physical fitness is the first requisite of happiness. — Joseph Pilates"
            ],
            "spiritual": [
                "We are not human beings having a spiritual experience. We are spiritual beings having a human experience. — Pierre Teilhard de Chardin",
                "The spiritual journey is the unlearning of fear and the acceptance of love. — Marianne Williamson",
                "Quiet the mind and the soul will speak. — Ma Jaya Sati Bhagavati",
                "Look within. Within is the fountain of good, and it will ever bubble up, if thou wilt ever dig. — Marcus Aurelius",
                "Just as a candle cannot burn without fire, men cannot live without a spiritual life. — Buddha",
                "The privilege of a lifetime is to become who you truly are. — Carl Jung",
                "You have to grow from the inside out. None can teach you, none can make you spiritual. There is no other teacher but your own soul. — Swami Vivekananda",
                "He who knows others is wise; he who knows himself is enlightened. — Lao Tzu",
                "Your task is not to seek for love, but merely to seek and find all the barriers within yourself that you have built against it. — Rumi",
                "Within you, there is a stillness and a sanctuary to which you can retreat at any time and be yourself. — Hermann Hesse"
            ],
            "mental health": [
                "What lies behind us and what lies before us are tiny matters compared to what lies within us. — Ralph Waldo Emerson",
                "Mental health is not a destination, but a process. It's about how you drive, not where you're going. — Noam Shpancer",
                "Self-care is how you take your power back. — Lalah Delia",
                "You don't have to control your thoughts; you just have to stop letting them control you. — Dan Millman",
                "Out of suffering have emerged the strongest souls; the most massive characters are seared with scars. — Kahlil Gibran",
                "My recovery from manic depression has been an evolution, not a sudden miracle. — Patty Duke",
                "I am not afraid of storms, for I am learning how to sail my ship. — Louisa May Alcott",
                "Happiness can be found even in the darkest of times, if one only remembers to turn on the light. — Albus Dumbledore",
                "You, as much as anyone in the entire universe, deserve your love and affection. — Buddha",
                "There is a crack in everything, that's how the light gets in. — Leonard Cohen"
            ],
            "motivation": [
                "The only way to do great work is to love what you do. — Steve Jobs",
                "It always seems impossible until it's done. — Nelson Mandela",
                "The future belongs to those who believe in the beauty of their dreams. — Eleanor Roosevelt",
                "Aim for the moon. If you miss, you may hit a star. — W. Clement Stone",
                "Do not wait to strike till the iron is hot; but make it hot by striking. — William Butler Yeats",
                "Your talent determines what you can do. Your motivation determines how much you are willing to do. — Lou Holtz",
                "Don't watch the clock; do what it does. Keep going. — Sam Levenson",
                "If you can dream it, you can do it. — Walt Disney",
                "The starting point of all achievement is desire. — Napoleon Hill",
                "Keep your face always toward the sunshine - and shadows will fall behind you. — Walt Whitman"
            ]
        }
        
        genre = parameter.lower().strip()
        allowed_genres = list(vault.keys())
        
        if genre not in allowed_genres:
            genre = "motivation"  # standard fallback
            
        import random
        # Filter quotes to prevent duplicates from the history
        available_quotes = [q for q in vault[genre] if q not in self.quote_history]
        
        if not available_quotes:
            # If all quotes from this genre have been served recently, clear history to reset
            available_quotes = vault[genre]
            self.quote_history = [q for q in self.quote_history if q not in vault[genre]]
            
        quote = random.choice(available_quotes)
        
        # Add to history (limit buffer to 15 quotes globally)
        self.quote_history.append(quote)
        if len(self.quote_history) > 15:
            self.quote_history.pop(0)
            
        return True, f"Here is a quote from the {genre} vault: \"{quote}\""

    def countdown_timer(self, parameter):
        import datetime
        import re
        
        target_hour = None
        target_min = 0
        
        clean_param = " ".join(parameter.lower().split())
        
        # Try to parse 12-hour AM/PM format (e.g. "6:30 pm", "12 am", "10:00 am", "6 p.m.")
        match_12 = re.match(r'(\d{1,2})(?:[:.\s](\d{2}))?\s*(a\.?m\.?|p\.?m\.?)', clean_param)
        if match_12:
            try:
                hr = int(match_12.group(1))
                mn = int(match_12.group(2)) if match_12.group(2) else 0
                period = match_12.group(3).replace('.', '')
                
                if hr < 1 or hr > 12 or mn < 0 or mn > 59:
                    return False, "Invalid 12-hour time parameters."
                    
                if period == "pm" and hr != 12:
                    target_hour = hr + 12
                elif period == "am" and hr == 12:
                    target_hour = 0
                else:
                    target_hour = hr
                    
                target_min = mn
            except Exception:
                return False, "Failed to parse 12-hour countdown time."
        else:
            # Fallback to 24-hour HH:MM format
            try:
                target_parts = list(map(int, parameter.split(":")))
                if len(target_parts) != 2:
                    return False, "Invalid time format for countdown. Use HH:MM or 12-hour AM/PM format."
                target_hour, target_min = target_parts
                if target_hour < 0 or target_hour > 23 or target_min < 0 or target_min > 59:
                    return False, "Invalid 24-hour time parameters."
            except Exception:
                return False, "Invalid time format for countdown."
                
        now = datetime.datetime.now()
        target_time = now.replace(hour=target_hour, minute=target_min, second=0, microsecond=0)
        
        if target_time < now:
            target_time += datetime.timedelta(days=1)
            
        delta = target_time - now
        total_seconds = int(delta.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        
        time_msg = ""
        if hours > 0:
            time_msg += f"{hours} hour{'s' if hours > 1 else ''}"
        if minutes > 0:
            if time_msg:
                time_msg += " and "
            time_msg += f"{minutes} minute{'s' if minutes > 1 else ''}"
            
        if not time_msg:
            time_msg = "less than a minute"
            
        return True, f"There are {time_msg} remaining until the target destination of {parameter}, boss."

    # ─────────────────────────────────────────────────────────────────────────
    # CLOCK TIMER
    # ─────────────────────────────────────────────────────────────────────────

    def open_clock(self):
        """
        Opens the Windows Clock app. No timer automation is performed.
        """
        print("[CLOCK] Opening Windows Clock...")
        try:
            # Kill existing Clock for a clean fresh window
            subprocess.run(["taskkill", "/F", "/IM", "Time.exe"], capture_output=True, timeout=3)
            time.sleep(0.5)
        except Exception:
            pass

        try:
            subprocess.Popen("start ms-clock:", shell=True)
            return True, "Clock opened, boss."
        except Exception as e:
            print(f"[CLOCK] Error: {e}")
            return False, "Could not open clock, boss."

    # ─────────────────────────────────────────────────────────────────────────
    # STUDY MODE WORKFLOW
    # ─────────────────────────────────────────────────────────────────────────
    # STUDY MODE WORKFLOW
    # ─────────────────────────────────────────────────────────────────────────

    def _close_distracting_apps(self):
        """
        Closes ALL running GUI applications except for a protected blacklist.
        Returns a dictionary: {"detected": [], "closed": [], "skipped": []}
        """
        print("[CLEANUP]")
        print("Scanning Applications")
        print("Protected: VS Code")
        print("Protected: Terminal")

        # ── Absolute no-touch set (VS Code + Terminal + system) ──────────────
        NEVER_KILL = {
            # VS Code
            "code.exe", "code - insiders.exe", "codium.exe",
            "code helper.exe", "code helper (gpu).exe",
            "code helper (plugin).exe", "code helper (renderer).exe",
            # Windows Terminal and Shells
            "windowsterminal.exe", "wt.exe", "openconsoled.exe",
            "cmd.exe", "powershell.exe", "pwsh.exe", "bash.exe",
            "sh.exe", "zsh.exe", "mintty.exe", "conhost.exe",
            # Python runtime
            "python.exe", "pythonw.exe", "py.exe",
            # Core Windows OS and Services
            "explorer.exe", "taskmgr.exe", "dwm.exe", "winlogon.exe",
            "csrss.exe", "smss.exe", "wininit.exe", "services.exe",
            "lsass.exe", "svchost.exe", "system", "registry",
            "sihost.exe", "fontdrvhost.exe", "audiodg.exe",
            "searchindexer.exe", "runtimebroker.exe", "startmenuexperiencehost.exe",
            "textinputhost.exe", "shellexperiencehost.exe", "taskhostw.exe",
            "ctfmon.exe", "spoolsv.exe", "msdtc.exe", "systemsettings.exe",
            "applicationframehost.exe",
            # Security / antivirus
            "mpcmdrun.exe", "msmpeng.exe", "nissrv.exe", "securityhealthservice.exe",
        }

        detected = []
        closed = []
        skipped = []
        procs_to_wait = []

        try:
            import psutil
            import ctypes

            EnumWindows = ctypes.windll.user32.EnumWindows
            EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int))
            GetWindowThreadProcessId = ctypes.windll.user32.GetWindowThreadProcessId
            IsWindowVisible = ctypes.windll.user32.IsWindowVisible

            visible_pids = set()
            def foreach_window(hwnd, lParam):
                if IsWindowVisible(hwnd):
                    pid = ctypes.c_uint()
                    GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                    visible_pids.add(pid.value)
                return True

            EnumWindows(EnumWindowsProc(foreach_window), 0)

            for proc in psutil.process_iter(["pid", "name"]):
                try:
                    pname = (proc.info["name"] or "").lower().strip()
                    pid = proc.info["pid"]

                    if pid <= 4:
                        continue

                    if pname in NEVER_KILL:
                        continue
                        
                    KNOWN_BACKGROUND_APPS = ["brave.exe", "chrome.exe", "firefox.exe", "opera.exe", "operagx.exe", "msedge.exe", "spotify.exe", "discord.exe"]
                    is_known_background = False
                    
                    if pname in KNOWN_BACKGROUND_APPS:
                        # Protect VS Code WebView2
                        if pname == "msedge.exe":
                            exe_path = (proc.exe() or "").lower()
                            if "appdata\\local\\microsoft\\edgewebview" in exe_path or "edge" not in exe_path:
                                continue
                        # Protect Brave updaters
                        if pname == "brave.exe":
                            exe_path = (proc.exe() or "").lower()
                            if "update" in exe_path:
                                continue
                        is_known_background = True

                    if pid in visible_pids or is_known_background:
                        detected.append(pname)
                        print(f"Closing: {pname}")
                        proc.terminate()
                        procs_to_wait.append((proc, pname))
                except (psutil.NoSuchProcess, psutil.AccessDenied, Exception):
                    if 'pname' in locals():
                        skipped.append(pname)

            # Wait for all signaled processes to actually terminate
            if procs_to_wait:
                procs = [p for p, _ in procs_to_wait]
                gone, alive = psutil.wait_procs(procs, timeout=3.0)
                
                for p in gone:
                    for proc, pname in procs_to_wait:
                        if p == proc:
                            closed.append(pname)
                            print(f"Closed: {pname}")
                            break
                            
                for p in alive:
                    for proc, pname in procs_to_wait:
                        if p == proc:
                            try:
                                p.kill()
                                closed.append(pname)
                                print(f"Closed: {pname}")
                            except Exception:
                                skipped.append(pname)
                            break

        except Exception as e:
            print(f"[CLEANUP] Error during cleanup: {e}")

        # Safety net: use taskkill for common browsers
        try:
            subprocess.run(["taskkill", "/F", "/IM", "brave.exe"], capture_output=True, timeout=3)
        except Exception:
            pass

        print("Cleanup Complete")
        return {"detected": detected, "closed": closed, "skipped": skipped}



    def activate_study_mode(self):
        """
        Full Study Mode workflow:
        1. Close applications (safe blacklist).
        2. Open Windows Clock.
        3. Wait 2 seconds.
        4. Open Brave -> lofi YouTube study stream.
        5. Wait 2 seconds.
        6. Open Brave -> Gemini in a new tab.
        7. Open WhatsApp (desktop app or web fallback).
        8. Open File Explorer.
        9. Wait 2 seconds.
        """
        print("[MODE] Starting Workflow")
        STUDY_LOFI_URL = "https://youtu.be/Yys43tMxMoc"
        GEMINI_URL     = "https://gemini.google.com"
        WHATSAPP_URL   = "https://web.whatsapp.com"

        brave_path = self._get_browser_path("brave")

        # ── Step 1: Close apps ────────────────────────────────────
        try:
            cleanup_results = self._close_distracting_apps()
            if cleanup_results:
                print(f"[CLEANUP] Detected: {len(cleanup_results.get('detected', []))} apps")
                print(f"[CLEANUP] Closed: {len(cleanup_results.get('closed', []))} apps")
                print(f"[CLEANUP] Skipped: {len(cleanup_results.get('skipped', []))} apps")
                print("[CLEANUP] Verification: Cleanup completed successfully.")
        except Exception as e:
            print(f"[CLEANUP] Warning: app-close step failed — {e}")

        # ── Step 2: Open Clock ────────────────────────
        try:
            self.open_clock()
        except Exception as e:
            print(f"[STUDY MODE] Warning: Clock step failed — {e}")
        time.sleep(2.0)

        # ── Step 3: Open Brave → Lofi Study Stream ────────────────────────────
        try:
            if brave_path:
                cmd = f'"{brave_path}" --autoplay-policy=no-user-gesture-required "{STUDY_LOFI_URL}"'
                subprocess.Popen(cmd, shell=True)
            else:
                webbrowser.open(STUDY_LOFI_URL)
        except Exception as e:
            print(f"[STUDY MODE] Warning: lofi step failed — {e}")
        time.sleep(2.0)

        # ── Step 4: Open Brave → Gemini ───────────────────────────────────────
        try:
            if brave_path:
                cmd = f'"{brave_path}" "{GEMINI_URL}"'
                subprocess.Popen(cmd, shell=True)
            else:
                webbrowser.open(GEMINI_URL)
        except Exception as e:
            print(f"[STUDY MODE] Warning: Gemini step failed — {e}")

        # ── Step 5: Open WhatsApp ─────────────────────────────────────────────
        try:
            whatsapp_uwp_cmd = "start whatsapp:"
            whatsapp_desktop = os.path.join(os.environ.get("LocalAppData", ""), "WhatsApp", "WhatsApp.exe")
            whatsapp_ms_store = os.path.join(os.environ.get("LocalAppData", ""), "Microsoft", "WindowsApps", "WhatsApp.exe")

            if os.path.exists(whatsapp_desktop):
                subprocess.Popen(f'"{whatsapp_desktop}"', shell=True)
            elif os.path.exists(whatsapp_ms_store):
                subprocess.Popen(f'"{whatsapp_ms_store}"', shell=True)
            else:
                subprocess.Popen(whatsapp_uwp_cmd, shell=True)
        except Exception as e:
            try:
                if brave_path:
                    subprocess.Popen(f'"{brave_path}" "{WHATSAPP_URL}"', shell=True)
                else:
                    webbrowser.open(WHATSAPP_URL)
            except Exception as e2:
                pass

        # ── Step 6: Open File Explorer ────────────────────────────────────────
        try:
            subprocess.Popen("explorer.exe", shell=True)
        except Exception as e:
            pass
        time.sleep(2.0)

        return True, "study mode activated"

    def activate_developer_mode(self):
        """
        Full Developer Mode workflow:
        1. Close applications (safe blacklist).
        2. Open VS Code.
        3. Open Windows Clock.
        4. Wait 2 seconds.
        5. Open Brave -> DEV lofi YouTube stream.
        6. Wait 2 seconds.
        7. Open Claude in a new Brave tab.
        8. Wait 2 seconds.
        9. Open Gemini in a new Brave tab.
        10. Wait 2 seconds.
        """
        print("[MODE] Starting Workflow")
        DEV_LOFI_URL  = "https://youtu.be/b3TOVBNSJDA"
        CLAUDE_URL    = "https://claude.ai"
        GEMINI_URL    = "https://gemini.google.com"

        brave_path = self._get_browser_path("brave")

        # ── Step 1: Close apps ────────────────────────────────────
        try:
            cleanup_results = self._close_distracting_apps()
            if cleanup_results:
                print(f"[CLEANUP] Detected: {len(cleanup_results.get('detected', []))} apps")
                print(f"[CLEANUP] Closed: {len(cleanup_results.get('closed', []))} apps")
                print(f"[CLEANUP] Skipped: {len(cleanup_results.get('skipped', []))} apps")
                print("[CLEANUP] Verification: Cleanup completed successfully.")
        except Exception as e:
            print(f"[CLEANUP] Warning: app-close step failed — {e}")

        # ── Step 2: Open VS Code (focus if running, launch if not) ────────────
        try:
            vscode_running = False
            try:
                import psutil
                for proc in psutil.process_iter(["name", "exe"]):
                    pname = (proc.info.get("name") or "").lower()
                    pexe  = (proc.info.get("exe")  or "").lower()
                    if "code" in pname or "code" in pexe:
                        vscode_running = True
                        break
            except Exception:
                pass

            if vscode_running:
                subprocess.Popen(
                    'powershell -NoProfile -Command "'
                    'Add-Type -TypeDefinition \'using System;using System.Runtime.InteropServices;'
                    'public class W{[DllImport(\\"user32.dll\\")]public static extern bool SetForegroundWindow(IntPtr h);}\';'
                    '$p=Get-Process code -ErrorAction SilentlyContinue|Select-Object -First 1;'
                    'if($p){[W]::SetForegroundWindow($p.MainWindowHandle)}"',
                    shell=True
                )
            else:
                vscode_paths = [
                    os.path.join(os.environ.get("LocalAppData", ""), "Programs", "Microsoft VS Code", "Code.exe"),
                    r"C:\Program Files\Microsoft VS Code\Code.exe",
                    r"C:\Program Files (x86)\Microsoft VS Code\Code.exe",
                ]
                launched = False
                for vsp in vscode_paths:
                    if os.path.exists(vsp):
                        subprocess.Popen(f'"{vsp}"', shell=True)
                        launched = True
                        break
                if not launched:
                    subprocess.Popen("code", shell=True)
        except Exception as e:
            print(f"[DEVELOPER MODE] Warning: VS Code step failed — {e}")

        # ── Step 3: Open Clock ────────────────────────
        try:
            self.open_clock()
        except Exception as e:
            print(f"[DEVELOPER MODE] Warning: Clock step failed — {e}")
        time.sleep(2.0)

        # ── Step 4: Open Brave → Dev Lofi Stream ──────────────────────────────
        try:
            if brave_path:
                cmd = f'"{brave_path}" --autoplay-policy=no-user-gesture-required "{DEV_LOFI_URL}"'
                subprocess.Popen(cmd, shell=True)
            else:
                webbrowser.open(DEV_LOFI_URL)
        except Exception as e:
            print(f"[DEVELOPER MODE] Warning: lofi step failed — {e}")
        time.sleep(2.0)

        # ── Step 5: Open Claude in new Brave tab ──────────────────────────────
        try:
            if brave_path:
                cmd = f'"{brave_path}" "{CLAUDE_URL}"'
                subprocess.Popen(cmd, shell=True)
            else:
                webbrowser.open(CLAUDE_URL)
        except Exception as e:
            print(f"[DEVELOPER MODE] Warning: Claude step failed — {e}")
        time.sleep(2.0)

        # ── Step 6: Open Gemini in new Brave tab ──────────────────────────────
        try:
            if brave_path:
                cmd = f'"{brave_path}" "{GEMINI_URL}"'
                subprocess.Popen(cmd, shell=True)
            else:
                webbrowser.open(GEMINI_URL)
        except Exception as e:
            print(f"[DEVELOPER MODE] Warning: Gemini step failed — {e}")
        time.sleep(2.0)

        return True, "Dev Mode Activated"


    def activate_fun_mode(self):
        """
        Full Fun Mode workflow:
        1. Close applications (safe blacklist).
        2. Open Windows Clock.
        3. Wait 2 seconds.
        4. Open Opera GX -> YouTube.
        5. Wait 2 seconds.
        6. Open Opera GX -> YouTube Music in a new tab.
        """
        print("[MODE] Starting Workflow")
        YOUTUBE_URL = "https://www.youtube.com"
        YT_MUSIC_URL = "https://music.youtube.com"

        opera_gx_path = self._get_browser_path("operagx")

        # ── Step 1: Close apps ────────────────────────────────────
        try:
            cleanup_results = self._close_distracting_apps()
            if cleanup_results:
                print(f"[CLEANUP] Detected: {len(cleanup_results.get('detected', []))} apps")
                print(f"[CLEANUP] Closed: {len(cleanup_results.get('closed', []))} apps")
                print(f"[CLEANUP] Skipped: {len(cleanup_results.get('skipped', []))} apps")
                print("[CLEANUP] Verification: Cleanup completed successfully.")
        except Exception as e:
            print(f"[CLEANUP] Warning: app-close step failed — {e}")

        # ── Step 2: Open Clock ────────────────────────
        try:
            self.open_clock()
        except Exception as e:
            print(f"[FUN MODE] Warning: Clock step failed — {e}")
        time.sleep(2.0)

        # ── Step 3: Open Opera GX → YouTube ──────────────────────────────
        try:
            if opera_gx_path:
                cmd = f'"{opera_gx_path}" "{YOUTUBE_URL}"'
                subprocess.Popen(cmd, shell=True)
            else:
                webbrowser.open(YOUTUBE_URL)
        except Exception as e:
            print(f"[FUN MODE] Warning: YouTube step failed — {e}")
        time.sleep(2.0)

        # ── Step 4: Open Opera GX → YouTube Music ──────────────────────────────
        try:
            if opera_gx_path:
                cmd = f'"{opera_gx_path}" "{YT_MUSIC_URL}"'
                subprocess.Popen(cmd, shell=True)
            else:
                webbrowser.open(YT_MUSIC_URL)
        except Exception as e:
            print(f"[FUN MODE] Warning: YouTube Music step failed — {e}")

        return True, "Fun Mode Activated"

    def activate_deep_mode(self):
        """
        Full Deep Mode workflow:
        1. Close applications (safe blacklist).
        2. Open Windows Clock.
        3. Wait 2 seconds.
        4. Open Chrome -> YouTube.
        5. Wait 2 seconds.
        6. Open Notepad.
        """
        print("[MODE] Starting Workflow")
        YOUTUBE_URL = "https://www.youtube.com"

        chrome_path = self._get_browser_path("chrome")

        # ── Step 1: Close apps ────────────────────────────────────
        try:
            cleanup_results = self._close_distracting_apps()
            if cleanup_results:
                print(f"[CLEANUP] Detected: {len(cleanup_results.get('detected', []))} apps")
                print(f"[CLEANUP] Closed: {len(cleanup_results.get('closed', []))} apps")
                print(f"[CLEANUP] Skipped: {len(cleanup_results.get('skipped', []))} apps")
                print("[CLEANUP] Verification: Cleanup completed successfully.")
        except Exception as e:
            print(f"[CLEANUP] Warning: app-close step failed — {e}")

        # ── Step 2: Open Clock ────────────────────────
        try:
            self.open_clock()
        except Exception as e:
            print(f"[DEEP MODE] Warning: Clock step failed — {e}")
        time.sleep(2.0)

        # ── Step 3: Open Chrome → YouTube ──────────────────────────────
        try:
            if chrome_path:
                cmd = f'"{chrome_path}" "{YOUTUBE_URL}"'
                subprocess.Popen(cmd, shell=True)
            else:
                webbrowser.open(YOUTUBE_URL)
        except Exception as e:
            print(f"[DEEP MODE] Warning: YouTube step failed — {e}")
        time.sleep(2.0)

        # ── Step 4: Open Notepad ──────────────────────────────
        try:
            subprocess.Popen("notepad.exe", shell=True)
        except Exception as e:
            print(f"[DEEP MODE] Warning: Notepad step failed — {e}")

        return True, "Deep Mode Activated"

    def activate_vision_mode(self):
        """
        Launches the Vision Mode application.
        Ensures it runs as a detached independent process.
        """
        import psutil
        import sys
        
        # Check if already running
        for proc in psutil.process_iter(['name', 'cmdline']):
            try:
                cmdline = proc.info.get('cmdline') or []
                if 'python' in (proc.info.get('name') or '').lower() and any('vision_launcher.py' in cmd for cmd in cmdline):
                    return True, "Vision Mode is already active boss."
            except Exception:
                pass
                
        print("[VISION] Starting")
        try:
            # CREATE_NEW_PROCESS_GROUP (0x00000200) runs it completely detached
            DETACHED_PROCESS = 0x00000008
            CREATE_NEW_PROCESS_GROUP = 0x00000200
            
            venv_python = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vision_venv", "Scripts", "python.exe")
            if not os.path.exists(venv_python):
                venv_python = sys.executable

            subprocess.Popen(
                [venv_python, "vision_launcher.py"],
                creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
            )
            time.sleep(1.5)
            
            # Verify running
            is_running = False
            for proc in psutil.process_iter(['name', 'cmdline']):
                try:
                    cmdline = proc.info.get('cmdline') or []
                    if 'python' in (proc.info.get('name') or '').lower() and any('vision_launcher.py' in cmd for cmd in cmdline):
                        is_running = True
                        break
                except Exception:
                    pass
            
            if is_running:
                print("[VISION] Running")
                return True, "Vision Mode Started"
            else:
                print("[VISION] Launch Failed")
                return False, "Unable to start Vision Mode boss."
                
        except Exception as e:
            print(f"[VISION] Launch Failed: {e}")
            return False, "Unable to start Vision Mode boss."

    def deactivate_vision_mode(self):
        """
        Locates the Vision Mode application and safely terminates it.
        """
        import psutil
        
        print("[VISION] Stopping")
        found_process = False
        
        for proc in psutil.process_iter(['name', 'cmdline']):
            try:
                cmdline = proc.info.get('cmdline') or []
                if 'python' in (proc.info.get('name') or '').lower() and any('vision_launcher.py' in cmd for cmd in cmdline):
                    found_process = True
                    try:
                        proc.terminate()
                        gone, alive = psutil.wait_procs([proc], timeout=3.0)
                        if alive:
                            proc.kill()
                    except Exception:
                        pass
            except Exception:
                pass
                
        if found_process:
            print("[VISION] Stopped")
            return True, "Vision Mode Stopped"
        else:
            return False, "Vision Mode is not currently active boss."


# --- Manual Test Suite ---
if __name__ == "__main__":
    controller = OSController()
    
    # Simulating what the Brain will send us later
    print("\n--- Running OS Controller Test 1: App Launch ---")
    mock_brain_output_1 = {
        "action": "launch_app",
        "target": "notepad",
        "parameter": "none"
    }
    success, message = controller.execute_command(mock_brain_output_1)
    print(f"Visual Verification Notice: {message} | Status: {success}")

    print("\n--- Running OS Controller Test 2: Web Search ---")
    mock_brain_output_2 = {
        "action": "launch_app",
        "target": "chrome",
        "parameter": "how to build an AI voice assistant in Python"
    }
    success, message = controller.execute_command(mock_brain_output_2)
    print(f"Visual Verification Notice: {message} | Status: {success}")
