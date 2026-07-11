import json
import re
try:
    import ollama
except ImportError:
    ollama = None

class SmaranBrain:
    def __init__(self, prefer_offline=False):
        self.prefer_offline = prefer_offline
        self.use_ollama = False
        self.history = []  # Maintain conversation memory
        
        # Test connection to local Ollama server if not preferred offline and library is available
        if not self.prefer_offline and ollama is not None:
            try:
                models_info = ollama.list()
                model_names = [m['model'] for m in models_info.get('models', [])]
                
                # Dynamic model matching to support any variant names (e.g. llama3:latest, llama3:8b, llama3)
                llama3_models = [m for m in model_names if 'llama3' in m.lower()]
                phi3_models = [m for m in model_names if 'phi3' in m.lower()]
                
                if llama3_models:
                    self.model = llama3_models[0]
                    self.use_ollama = True
                    print(f"🤖 [SMARAN COGNITIVE] Connected to local Ollama. Deploying {self.model} core...")
                elif phi3_models:
                    self.model = phi3_models[0]
                    self.use_ollama = True
                    print(f"🤖 [SMARAN COGNITIVE] Connected to local Ollama. Deploying {self.model} core...")
                elif model_names:
                    self.model = model_names[0]
                    self.use_ollama = True
                    print(f"🤖 [SMARAN COGNITIVE] Connected to local Ollama. Deploying {self.model} core...")
            except Exception:
                print("🔌 [SMARAN COGNITIVE] Ollama server offline. Reverting to local heuristic syntax core...")

    def think(self, user_input):
        """Translates natural speech strings directly into actionable system intents"""
        text = user_input.lower().strip()
        
        # Strip wake words/names from the input text before matching conversational patterns
        if text.startswith("hey smaran "):
            text = text[11:]
        elif text.startswith("smaran "):
            text = text[7:]
            
        if text.endswith(" smaran"):
            text = text[:-7]
            
        text = text.strip()

        # Check conversational patterns first to override LLM and heuristics
        # Pattern 1: How is it doing
        if any(p in text for p in ["how are you", "how're you", "how are you doing", "how you doing"]):
            return {
                "action": "conversational_reply",
                "target": "none",
                "parameter": "none",
                "spoken_response": "I am operating at peak efficiency, boss. Thank you for asking. How can I assist you today?"
            }
            
        # Pattern 2: Identity (introducing itself)
        if any(p in text for p in ["whats ur name", "whats your name", "what's your name", "what is your name", "who are you", "who are u", "what do people call you", "what are you called", "what do they call you"]):
            return {
                "action": "conversational_reply",
                "target": "none",
                "parameter": "none",
                "spoken_response": "I am Smaran, your personal AI assistant, boss. I can open apps, play music, answer questions, and much more. Just say the word."
            }
            
        # Pattern 3: Creator (Strict predefined response)
        if any(p in text for p in ["who created you", "who created u", "who made you", "who made u", "who developed you", "who developed u"]):
            return {
                "action": "conversational_reply",
                "target": "none",
                "parameter": "none",
                "spoken_response": "I was created by my owner Jeevan Krishna, boss."
            }

        # Pattern 4: Say hello to others/guests/friends
        if any(p in text for p in ["say hello to others", "say hello to guests", "say hello to friends", "say hello to everyone", "say hello to people", "greet my guests", "greet my friends", "greet the guests"]):
            return {
                "action": "conversational_reply",
                "target": "none",
                "parameter": "none",
                "spoken_response": "Hello everyone! I am Smaran, your computing and home automation assistant. It is a pleasure to meet you."
            }

        # Phonetic mapping for workspaces to override LLM/heuristics
        chatgpt_variants = ["chat", "cha", "gpt", "chatgpt"]
        claude_variants = ["claud", "cloud", "claw", "clawed", "cla", "claude"]
        # Grok: original + expanded phonetic variants (grook, rook, rock)
        # NOTE: "clock" was removed — it caused "open clock" to route to Grok instead
        # of the Windows Clock app. Only keep variants that cannot be misheard as an app.
        grok_variants = ["grow", "gro", "grau", "rok", "grok", "grook", "rook"]
        gemini_variants = ["gemini"]
        # Perplexity: catches per+plex combos and phonetic mishearings
        # We require at least one 4+ char fragment to avoid triggering on unrelated words like "per" alone
        perplexity_direct = ["perplexity", "perplex", "plecks", "plexity"]
        perplexity_partial = ["plex", "pleks"]  # Needs "per" or "city" nearby

        has_chatgpt = any(v in text.split() for v in chatgpt_variants) or any(v in text for v in ["chatgpt", "chat-gpt", "chat gpt"])
        has_claude = any(v in text.split() for v in claude_variants) or any(v in text for v in ["claude"])
        has_grok = any(v in text.split() for v in grok_variants) or any(v in text for v in ["grok"])
        has_gemini = any(v in text.split() for v in gemini_variants) or any(v in text for v in ["gemini"])

        # Perplexity detection: direct match OR (partial + context syllables)
        has_perplexity = (
            any(v in text for v in perplexity_direct) or
            (any(v in text for v in perplexity_partial) and any(s in text for s in ["per", "city", "ity", "flex"])) or
            ("per" in text.split() and "plex" in text) or
            ("flex" in text.split() and any(s in text for s in ["per", "plex"]))
        )

        # Guard: only route to workspace if query is clearly about opening an AI browser tool,
        # NOT when the matching word is part of an OS app request (e.g. "open clock").
        _os_app_words = {"clock", "calc", "calculator", "notepad", "explorer", "timer", "alarm"}
        _ws_words = set(text.split())
        _is_os_request = bool(_ws_words & _os_app_words)

        if (has_chatgpt or has_claude or has_grok or has_gemini or has_perplexity) \
                and any(w in text for w in ["open", "launch", "workspace"]) \
                and not _is_os_request:
            detected_workspaces = []
            if has_gemini: detected_workspaces.append("gemini")
            if has_chatgpt: detected_workspaces.append("chatgpt")
            if has_claude: detected_workspaces.append("claude")
            if has_grok: detected_workspaces.append("grok")
            if has_perplexity: detected_workspaces.append("perplexity")
            
            # Detect browser
            browsers = ["operagx", "opera gx", "opera", "chrome", "firefox", "edge", "msedge", "brave", "safari", "browser"]
            browser_target = "browser"
            for b in browsers:
                if b in text:
                    browser_target = b
                    break
            normalized_browser = "msedge" if browser_target == "edge" else browser_target
            
            return {
                "action": "ecosystem_workspace",
                "target": normalized_browser,
                "parameter": ",".join(detected_workspaces),
                "spoken_response": f"Launching {', '.join(detected_workspaces)} in {normalized_browser}, boss."
            }

        # If Ollama connection wasn't established yet, try to poll and connect dynamically
        if not self.use_ollama and not self.prefer_offline and ollama is not None:
            try:
                models_info = ollama.list()
                model_names = [m['model'] for m in models_info.get('models', [])]
                llama3_models = [m for m in model_names if 'llama3' in m.lower()]
                phi3_models = [m for m in model_names if 'phi3' in m.lower()]
                
                if llama3_models:
                    self.model = llama3_models[0]
                    self.use_ollama = True
                    print(f"🤖 [SMARAN COGNITIVE] Connected to local Ollama. Deploying {self.model} core...")
                elif phi3_models:
                    self.model = phi3_models[0]
                    self.use_ollama = True
                    print(f"🤖 [SMARAN COGNITIVE] Connected to local Ollama. Deploying {self.model} core...")
            except Exception:
                pass  # Ollama still offline, continue with heuristics

        if self.use_ollama:
            try:
                return self._think_llm(user_input)
            except Exception as e:
                print(f"⚠️ [SMARAN COGNITIVE ERROR] LLM inference failed: {e}. Falling back to heuristics...")
                
        # --- GROK REASONING LAYER ---
        # Route knowledge/reasoning queries to Grok BEFORE falling back to heuristics.
        # This fires ONLY if the query is NOT an automation command.
        if self._should_use_grok(text, user_input):
            return {
                "action": "grok_query",
                "target": "none",
                "parameter": user_input,  # Pass original unstripped text for best context
                "spoken_response": ""     # Filled in by main.py after the API call returns
            }

        return self._think_heuristics(user_input)

    def _think_llm(self, user_input):
        system_prompt = (
            "You are Smaran, a highly sophisticated, polite, and witty voice assistant. "
            "Address the user as 'sir' or 'ma'am'. Speak with a refined British cadence. "
            "You must analyze the user's request and respond strictly in valid JSON format. "
            "No extra markdown, no wrap blocks, only raw JSON.\n\n"
            "JSON Schema:\n"
            "{\n"
            '  "action": "launch_app" | "system_control" | "conversational_reply" | "shutdown" | "weather_scanner" | "morning_briefing" | "ecosystem_workspace" | "youtube_music" | "random_generator" | "wisdom_vault" | "countdown_timer",\n'
            '  "target": "chrome" | "msedge" | "firefox" | "opera" | "brave" | "operagx" | "opera gx" | "notepad" | "calculator" | "cmd" | "explorer" | "task manager" | "volume_up" | "volume_down" | "mute" | "none",\n'
            '  "parameter": "search query, URLs, comma-separated bounds like min,max, or target values/genres",\n'
            '  "spoken_response": "Your spoken conversational reply as Smaran"\n'
            "}\n\n"
            "STRICT RULES:\n"
            "1. 'target' MUST be chosen ONLY from the allowed list in the schema. Never invent new targets. If no listed target matches the app, set target to 'none'.\n"
            "2. If the user asks for weather, set action='weather_scanner', target='none', parameter='none'.\n"
            "3. If the user asks for a morning brief/briefing, set action='morning_briefing', target='none', parameter='none'.\n"
            "4. If the user wants to launch multiple workspace surfaces (any combinations of gemini, chatgpt, claude, grok), set action='ecosystem_workspace', target=requested_browser (or 'browser'), and parameter=comma-separated list of workspaces (e.g. 'gemini,chatgpt').\n"
            "5. If the user wants to play music or open YouTube Music, set action='youtube_music', target=requested_browser (or 'browser'), and parameter=song/artist name (or 'none' if no query).\n"
            "6. If the user wants a random number/value between two bounds, set action='random_generator', target='none', and parameter='min,max' (e.g. '5,20').\n"
            "7. If the user wants a quote/wisdom, set action='wisdom_vault', target='none', and parameter=requested genre ('courage', 'freedom', 'romance', 'history', 'grit', 'confidence', 'love', 'self-improvement', 'time-management', 'health', 'spiritual', 'mental health', 'motivation', or 'none').\n"
            "8. If the user wants a countdown timer or time remaining until a target 12-hour AM/PM time, set action='countdown_timer', target='none', and parameter=target time string (e.g. '6:30 PM' or '12:00 AM').\n"
            "9. If the user wants to stop, exit, shutdown, or tells you to go to sleep/goodnight/bye, set action='shutdown', target='none', parameter='none'.\n"
            "10. If the user asks for your name, what you are called, or who you are, you must clearly state that your name is Smaran.\n"
            "11. Ensure your 'spoken_response' sounds polished, interactive, and intelligent, like a premium assistant."
        )

        # Append current user prompt to history
        self.history.append({"role": "user", "content": user_input})

        try:
            # Build full message payload (System instruction + dialogue memory history)
            messages = [{"role": "system", "content": system_prompt}] + self.history

            response = ollama.chat(
                model=self.model,
                messages=messages,
                options={"temperature": 0.3}
            )

            reply_content = response['message']['content'].strip()
            
            # Clean markdown codeblocks if LLM returned them
            if reply_content.startswith("```json"):
                reply_content = reply_content[7:]
            if reply_content.startswith("```"):
                reply_content = reply_content[3:]
            if reply_content.endswith("```"):
                reply_content = reply_content[:-3]
            reply_content = reply_content.strip()

            intent = json.loads(reply_content)
            spoken_text = intent.get("spoken_response", "")

            # Append Smaran's spoken reply as assistant turn to context history
            self.history.append({"role": "assistant", "content": spoken_text})

            # Keep history window capped to prevent context overflow (last 12 exchanges)
            if len(self.history) > 12:
                self.history = self.history[-12:]

            return intent
        except Exception as e:
            # Remove failed turn from history to protect alignment
            if self.history and self.history[-1]["role"] == "user":
                self.history.pop()
            raise e

    def _should_use_grok(self, text: str, original_input: str) -> bool:
        """
        Determines if a query should be routed to Groq rather than automation/heuristics.

        Logic:
        1. AUTOMATION GUARD — if query matches ANY automation pattern, return False immediately.
           Automation always takes priority over Groq.
        2. TIER 1 — explicit reasoning/knowledge keywords → return True
        3. Otherwise → return False (let heuristics handle it)

        NOTE: Tier 2 (semantic fallback) was removed — it caused too many false positives
        with conversational phrases like "go ahead and stick", "let me know", etc.
        Groq only fires on clearly intentional knowledge/reasoning queries.
        """
        # ── STEP 1: AUTOMATION GUARD ──────────────────────────────────────────
        # These are definitive automation signals. If present, NEVER send to Groq.
        automation_signals = [
            # App / browser control
            "open", "launch", "start", "run", "close", "quit",
            # Web / search
            "search", "google", "look up", "find", "browse",
            # Media
            "play", "youtube", "music", "spotify",
            # Sleep / shutdown / exit
            "shutdown", "stop", "exit", "bye", "goodbye", "good bye",
            "sleep", "goodnight", "good night", "go to sleep",
            "deactivate", "wake up", "turn off", "see you",
            # System
            "volume up", "volume down", "increase volume", "decrease volume", "mute",
            # Smaran features
            "workspace", "study mode", "briefing", "brief me",
            "weather", "forecast", "countdown", "timer",
            "set timer", "start timer", "clock timer", "open clock",
            "random", "quote", "wisdom",
            # Calculator and notepad automation — must NOT go to Groq
            "calculate", "compute", "solve",
            "type ", "write ", "notepad",
            # Conversational short-circuits — must NOT go to Groq
            "okay", "ok", "go ahead", "never mind",
            "yes", "no", "sure", "alright", "got it",
            # Greetings handled by heuristics, not Groq
            "how are you", "how are you doing", "how you doing", "how're you",
            "hello", "hi", "hey", "yo", "sup", "wassup", "howdy",
            "good morning", "good afternoon", "good evening",
            "thank you", "thanks",
        ]
        for signal in automation_signals:
            sig_stripped = signal.strip()
            if sig_stripped:
                pattern = rf'\b{re.escape(sig_stripped)}\b'
                if signal.endswith(' '):
                    pattern = rf'\b{re.escape(sig_stripped)}\s'
                elif signal.startswith(' '):
                    pattern = rf'\s{re.escape(sig_stripped)}\b'
                
                if re.search(pattern, text):
                    return False

        # Block single-word inputs only (command fragments, wake artifacts)
        # Two-word knowledge queries like "explain recursion" must still reach Groq
        words = text.split()
        if len(words) <= 1:
            return False

        # Block if the first word is a command verb — these are imperative sentences
        command_first_words = [
            "open", "launch", "start", "play", "search", "run", "go",
            "close", "stop", "mute", "volume", "show", "display",
            "set", "turn", "activate", "deactivate", "enable", "disable",
            "increase", "decrease", "get", "fetch", "load",
        ]
        if words[0] in command_first_words:
            return False

        # ── STEP 2: TIER 1 — EXPLICIT KNOWLEDGE SIGNALS ───────────────────────
        # Only route to Groq when the user clearly wants knowledge/reasoning.
        # These are high-confidence indicators of an intentional question.
        knowledge_starters = [
            "research", "wikipedia",
            # Explanation requests
            "explain", "what is", "what are", "what was", "what were",
            "what does", "what do", "what would", "what will",
            "why is", "why are", "why was", "why were", "why does", "why do",
            "why would", "why can", "why should",
            "how is", "how are", "how does", "how do", "how can",
            "how would", "how should", "how to",
            # Summary / analysis
            "summarize", "summary of", "give me a summary",
            "analyze", "analysis of", "break down", "break it down",
            "simplify", "help me understand", "help me learn",
            "tell me about", "tell me more", "tell me the",
            "can you explain", "could you explain",
            # Comparison
            "compare", "difference between", "differences between",
            "versus", " vs ", "pros and cons", "advantages and disadvantages",
            "which is better", "which one is better",
            # Opinion / review
            "opinion on", "public opinion", "what people think",
            "review of", "overview of",
            # Current info / news
            "latest", "recent", "current events", "news about",
            "what happened", "what is happening",
            "who invented", "who discovered", "who is",
            "when was", "when did", "when is",
            "where is", "where was", "where does",
            # Learning signals
            "i want to know", "i need to know",
            "can you tell me", "could you tell me",
            "what are the", "what is the",
            "give me information", "give me details",
            "importance of", "definition of", "meaning of",
            "examples of", "types of", "kinds of",
        ]
        for signal in knowledge_starters:
            if signal in text:
                return True

        # Everything else → let heuristics handle it
        return False


    def _think_heuristics(self, user_input):

        text = user_input.lower().strip()
        
        # Strip wake words/names from the input text before matching shutdown/greetings
        if text.startswith("hey smaran "):
            text = text[11:]
        elif text.startswith("smaran "):
            text = text[7:]

        # Strip trailing " smaran" only when it's a wake-word artifact, NOT when
        # the user is dictating content (e.g. "open notepad and type hello i am smaran")
        _content_dictation = any(kw in text for kw in ["type ", "write ", "enter ", " say "])
        if text.endswith(" smaran") and not _content_dictation:
            text = text[:-7]

        text = text.strip()
        
        # Check for shutdown commands first (with expanded wake/sleep keywords)
        shutdown_phrases = [
            "stop", "exit", "bye", "goodbye", "shutdown", "shut down",
            "go to sleep", "sleep now", "turn off", "terminate",
            "goodnight", "good night", "see you", "that's all",
            "i'm done", "im done", "deactivate"
        ]
        for phrase in shutdown_phrases:
            if text == phrase or text.startswith(phrase + " ") or text.endswith(" " + phrase):
                return {
                    "action": "shutdown",
                    "target": "none",
                    "parameter": "none",
                    "spoken_response": "Goodbye boss. Shutting down systems now."
                }

        # --- DEVELOPER MODE RULE --- (checked before study mode)
        _dev_triggers = [
            "dev mode", "developer mode", "deve mode", "dev_mode", "devemode", "devmod",
            "develop mode", "develop", "development mode",
        ]
        _dev_fuzzy = [
            "dev", "deve", "loper", "oper", "devmod",
        ]
        _is_dev = any(t in text for t in _dev_triggers)
        if not _is_dev:
            words = text.split()
            _is_dev = any(w in _dev_fuzzy for w in words)
        if _is_dev:
            return {
                "action": "developer_mode",
                "target": "none",
                "parameter": "none",
                "spoken_response": "Activating Developer Mode boss."
            }

        # --- STUDY MODE RULE --- (checked before all other rules)
        _study_triggers = [
            "study mode", "studymod", "study_mode",
            "activate study", "start study", "enter study",
            # Phonetic/partial variants Whisper may hear
            "stud mode", "stdy mode", "studie mode",
            "studdy mode", "study mod",
        ]
        _study_fuzzy = [
            "stud", "stdy", "tudy", "udymod",
        ]
        _is_study = any(t in text for t in _study_triggers)
        if not _is_study:
            words = text.split()
            _is_study = any(w in _study_fuzzy for w in words)
        if _is_study:
            return {
                "action": "study_mode",
                "target": "none",
                "parameter": "none",
                "spoken_response": "Activating Study Mode boss."
            }

        # --- FUN MODE RULE ---
        _fun_triggers = ["fun mode", "fun_mode", "funmod"]
        _is_fun = any(t in text for t in _fun_triggers)
        if _is_fun:
            return {
                "action": "fun_mode",
                "target": "none",
                "parameter": "none",
                "spoken_response": "Activating Fun Mode boss."
            }

        # --- DEEP MODE RULE ---
        _deep_triggers = ["deep mode", "deep_mode", "deepmod"]
        _is_deep = any(t in text for t in _deep_triggers)
        if _is_deep:
            return {
                "action": "deep_mode",
                "target": "none",
                "parameter": "none",
                "spoken_response": "Activating Deep Mode boss."
            }

        # --- VISION MODE RULES ---
        _vision_activate_triggers = ["activate vision", "start vision", "vision mode", "enable vision"]
        if any(t in text for t in _vision_activate_triggers):
            return {
                "action": "activate_vision",
                "target": "none",
                "parameter": "none",
                "spoken_response": "Activating Vision Mode boss."
            }

        _vision_deactivate_triggers = ["lock vision", "disable vision", "stop vision", "close vision"]
        if any(t in text for t in _vision_deactivate_triggers):
            return {
                "action": "deactivate_vision",
                "target": "none",
                "parameter": "none",
                "spoken_response": "Disabling Vision Mode boss."
            }

        # Flexible pattern matching for common conversational questions
        # Pattern 1: How are you doing / how are you
        if any(p in text for p in ["how are you", "how're you", "how are you doing", "how you doing"]):
            return {
                "action": "conversational_reply",
                "target": "none",
                "parameter": "none",
                "spoken_response": "I am operating at peak efficiency, boss. Thank you for asking. How can I assist you today?"
            }

        # Pattern 1b: Greetings (hi, hello, hey, hiiii, heyy, yo, sup, etc.)
        greeting_triggers = [
            "hello", "hi", "hey", "hii", "hiii", "hiiii", "hiiiii",
            "heyy", "heyyy", "hey there", "hello there",
            "yo", "sup", "wassup", "what's up", "whats up",
            "good morning", "good afternoon", "good evening", "good night",
            "howdy", "greetings", "salutations",
        ]
        if any(text == g or text.startswith(g + " ") or text == g.rstrip() for g in greeting_triggers):
            return {
                "action": "conversational_reply",
                "target": "none",
                "parameter": "none",
                "spoken_response": (
                    "Hello boss! I am Smaran, your personal AI assistant. "
                    "I can open apps, play music, search the web, answer questions, "
                    "and much more. What can I do for you today?"
                )
            }
            
        # Pattern 2: Identity (name, who you are)
        if any(p in text for p in ["whats ur name", "whats your name", "what's your name", "what is your name", "who are you", "what do people call you", "what are you called"]):
            return {
                "action": "conversational_reply",
                "target": "none",
                "parameter": "none",
                "spoken_response": "I am Smaran, your personal AI assistant, boss. I can control your computer, open apps, play music, answer questions, and a lot more. Just say the word."
            }
            
        # Pattern 3: Creator / Owner (Jeevan Krishna)
        if any(p in text for p in ["who created you", "who created u", "who made you", "who made u", "who developed you", "who developed u"]):
            return {
                "action": "conversational_reply",
                "target": "none",
                "parameter": "none",
                "spoken_response": "I was created by my owner Jeevan Krishna, boss."
            }

        # Smaran conversational fallback responses
        conversational_responses = {
            "hello": "Hello boss! Great to hear from you. What can I do for you?",
            "hi": "Hey boss! I am online and ready. How can I help?",
            "hey": "Hey boss! Standing by. What do you need?",
            "hii": "Hello boss! How can I assist you today?",
            "hiii": "Hello boss! At your service.",
            "hiiii": "Hello boss! Always here when you need me.",
            "yo": "Yo boss! What's up? How can I help?",
            "sup": "All systems running smooth, boss. What do you need?",
            "howdy": "Howdy boss! Ready and waiting. What can I do for you?",
            "good morning": "Good morning boss! Hope you have a great day. How can I assist you?",
            "good afternoon": "Good afternoon boss! How can I help you today?",
            "good evening": "Good evening boss! What can I do for you?",
            "how are you": "I am operating at peak efficiency, boss. Thanks for asking! How can I help?",
            "who are you": "I am Smaran, your personal AI assistant, boss. I can open apps, play music, answer questions, and much more.",
            "what is your name": "My name is Smaran, boss. Your personal AI assistant, at your service.",
            "whats your name": "My name is Smaran, boss. Your personal AI assistant, at your service.",
            "what's your name": "My name is Smaran, boss. Your personal AI assistant, at your service.",
            "thank you": "Always a pleasure, boss!",
            "thanks": "Anytime, boss!",
            "okay": "Ready when you are, boss.",
            "ok": "Ready when you are, boss.",
        }

        # Check for simple greeting/conversational match
        # WORD-COUNT GUARD: only match if captured text is within 2 words of
        # the greeting length. Prevents "thank you for your attention, you."
        # (6 words) from matching "thank you" (2 words) via startswith.
        text_word_count = len(text.split())
        for greeting, reply in conversational_responses.items():
            greeting_word_count = len(greeting.split())
            if text == greeting or (
                text.startswith(greeting + " ") and
                text_word_count <= greeting_word_count + 2
            ):
                return {
                    "action": "conversational_reply",
                    "target": "none",
                    "parameter": "none",
                    "spoken_response": reply
                }

        # Standard heuristics fallback initialization
        intent = {
            "action": "conversational_reply",
            "target": "none",
            "parameter": "none",
            "spoken_response": "sorry i didnt understand."
        }

        # Pre-process: Identify target browser if explicitly mentioned in the text
        browsers = ["operagx", "opera gx", "opera", "chrome", "firefox", "edge", "msedge", "brave", "safari", "browser"]
        browser_target = "browser"  # Default fallback
        for b in browsers:
            if b in text:
                browser_target = b
                break

        # Normalize target browser name
        normalized_browser = "msedge" if browser_target == "edge" else browser_target

        # Create clean text by removing browser qualifiers to isolate tasks/parameters
        clean_text = text
        for b in ["operagx", "opera gx", "opera", "chrome", "firefox", "edge", "msedge", "brave", "safari", "browser"]:
            for suffix in [" browser", ""]:
                term_with_suffix = b + suffix
                if term_with_suffix in clean_text:
                    for prep in ["in ", "on ", "using ", "with ", "via ", "to "]:
                        clean_text = clean_text.replace(prep + term_with_suffix, "")
                    clean_text = clean_text.replace(term_with_suffix, "")
        clean_text = clean_text.strip()

        # --- RULE 1: ENVIRONMENTAL AWARENESS ---
        # Skill 1: Weather Scanner
        if ("weather" in clean_text or "forecast" in clean_text) and not any(s in clean_text for s in ["search", "google", "look up"]):
            return {
                "action": "weather_scanner",
                "target": "none",
                "parameter": "none",
                "spoken_response": "Scanning local weather systems for you, boss."
            }

        # Skill 8: Morning Briefing Aggregator
        if "briefing" in clean_text or "brief me" in clean_text or "morning brief" in clean_text:
            return {
                "action": "morning_briefing",
                "target": "none",
                "parameter": "none",
                "spoken_response": "Preparing your briefing, boss."
            }

        # --- RULE 2: MULTI-SURFACE WORKSPACE CONTROL ---
        # Skill 2: Ecosystem Workspace Launcher — includes Perplexity
        workspaces_list = ["gemini", "chatgpt", "claude", "grok", "perplexity"]
        detected_workspaces = [w for w in workspaces_list if w in clean_text]

        # Also check phonetic grok variants in clean_text
        # NOTE: "clock" and "rock" removed — they caused "open clock" to route to Grok
        grok_phonetics = ["grook", "rook", "grow", "gro", "grau", "rok"]
        if any(v in clean_text.split() for v in grok_phonetics) and "grok" not in detected_workspaces:
            detected_workspaces.append("grok")

        # Also check phonetic perplexity variants in clean_text
        perplexity_direct = ["perplex", "plecks", "plexity"]
        perplexity_partial = ["plex", "pleks"]
        has_perplexity_heuristic = (
            any(v in clean_text for v in perplexity_direct) or
            (any(v in clean_text for v in perplexity_partial) and any(s in clean_text for s in ["per", "city", "ity", "flex"]))
        )
        if has_perplexity_heuristic and "perplexity" not in detected_workspaces:
            detected_workspaces.append("perplexity")

        # Guard: don't fire workspace routing when the query is an OS app command
        # e.g. "open clock", "open timer", "open alarm" must NOT route to Grok/workspace
        _os_words_heuristic = {"clock", "timer", "alarm", "calculator", "calc", "notepad", "explorer"}
        _is_os_app_cmd = bool(set(clean_text.split()) & _os_words_heuristic)

        if len(detected_workspaces) >= 1 \
                and ("open" in clean_text or "launch" in clean_text or "workspace" in clean_text) \
                and not _is_os_app_cmd:
            return {
                "action": "ecosystem_workspace",
                "target": normalized_browser,
                "parameter": ",".join(detected_workspaces),
                "spoken_response": f"Launching {', '.join(detected_workspaces)} in {normalized_browser}, boss."
            }


        # Skill 4: YouTube Music Director
        if "youtube music" in clean_text or "play music" in clean_text or "music director" in clean_text:
            query = clean_text
            for term in ["on youtube music", "in youtube music", "to youtube music", "music director", "youtube music", "play music", "music", "play"]:
                query = query.replace(term, "")
            query = query.strip()
            if query in ["open", "launch", "start", "run", "play", ""]:
                query = ""
            param = query if query else "none"
            spoken = f"Opening YouTube Music search for {query}, boss." if query else "Opening your YouTube Music dashboard, boss."
            return {
                "action": "youtube_music",
                "target": normalized_browser,
                "parameter": param,
                "spoken_response": spoken
            }

        # Skill 7: Smart Google Search Interface
        if re.search(r'\bsearch\b', clean_text) or "look up" in clean_text or "google" in clean_text:
            query = clean_text
            for term in ["look up from google", "using google", "from google", "with google",
                         "search for", "on google", "look up", "search", "google",
                         "open", "and"]:
                if term in ["search", "google", "look up"]:
                    query = re.sub(rf'\b{re.escape(term)}\b', '', query, flags=re.IGNORECASE)
                else:
                    query = query.replace(term, "")
            query = " ".join(query.split()).strip()
            if query and query not in ["open", "launch", "and"]:
                return {
                    "action": "launch_app",
                    "target": normalized_browser,
                    "parameter": query,
                    "spoken_response": f"Searching for {query}, boss."
                }


        # --- RULE 2b: STANDALONE CALCULATOR COMMANDS ---
        # Detect: "calculate 100*2", "compute 50 divided by 5", "solve 10+5"
        # Fires BEFORE random/wisdom so "calculate" is never mistaken for another rule.
        for _calc_prefix in ["calculate ", "compute ", "solve "]:
            if clean_text.startswith(_calc_prefix):
                _expr_raw = clean_text[len(_calc_prefix):].strip()
                return {
                    "action": "calculator_compute",
                    "target": "calculator",
                    "parameter": _expr_raw,
                    "spoken_response": "Opening Calculator and computing the result, boss."
                }

        # --- RULE 3: ALGORITHMIC LOGIC ENGINES ---
        # Skill 5: Curated Wisdom Vault
        if "quote" in clean_text or "wisdom" in clean_text:
            genres = [
                "self-improvement", "self improvement", "time-management", "time management",
                "mental-health", "mental health", "motivation", "confidence", "spiritual",
                "romance", "history", "courage", "freedom", "health", "love", "grit"
            ]
            genre = "none"
            for g in genres:
                if g in clean_text:
                    genre = g
                    if g == "self improvement":
                        genre = "self-improvement"
                    elif g == "time management":
                        genre = "time-management"
                    elif g == "mental-health":
                        genre = "mental health"
                    break
            display_genre = genre if genre != "none" else "general wisdom"
            return {
                "action": "wisdom_vault",
                "target": "none",
                "parameter": genre,
                "spoken_response": f"Retrieving a curated quote from my {display_genre} vault, boss."
            }

        # Skill 3: Random Value Generator
        if any(kw in clean_text for kw in ["random", "generator", "generate", "pick", "choose"]) or \
                ("between" in clean_text and any(c.isdigit() for c in clean_text)):
            numbers = re.findall(r'\d+', clean_text)
            if len(numbers) >= 2:
                val_a = int(numbers[0])
                val_b = int(numbers[1])
                return {
                    "action": "random_generator",
                    "target": "none",
                    "parameter": f"{val_a},{val_b}",
                    "spoken_response": f"Generating a random number between {val_a} and {val_b}, boss."
                }
            else:
                return {
                    "action": "random_generator",
                    "target": "none",
                    "parameter": "1,10",
                    "spoken_response": "Generating a random number between 1 and 10, boss."
                }

        # Skill 6a: Clock Timer — "set timer for 45 minutes" / "open clock set timer 1 hour"
        _clock_timer_triggers = [
            "set timer", "set a timer", "start timer", "start a timer",
            "create timer", "create a timer", "open clock", "clock timer",
            "set the timer", "put a timer", "put timer",
        ]
        _is_clock_timer = any(t in clean_text for t in _clock_timer_triggers)
        if _is_clock_timer:
            total_minutes = 0
            # Match hours component: "1 hour", "2 hours"
            hr_match = re.search(r'(\d+)\s*hour', clean_text)
            if hr_match:
                total_minutes += int(hr_match.group(1)) * 60
            # Match minutes component: "45 minutes", "30 min", "45 mins"
            mn_match = re.search(r'(\d+)\s*min', clean_text)
            if mn_match:
                total_minutes += int(mn_match.group(1))
            # If neither, try bare number at the end: "set timer 20"
            if total_minutes == 0:
                bare = re.search(r'(\d+)\s*$', clean_text)
                if bare:
                    total_minutes = int(bare.group(1))
            if total_minutes > 0:
                if total_minutes >= 60:
                    h, m = divmod(total_minutes, 60)
                    dur_str = f"{h} hour{'s' if h>1 else ''}"
                    if m:
                        dur_str += f" and {m} minute{'s' if m>1 else ''}"
                else:
                    dur_str = f"{total_minutes} minute{'s' if total_minutes>1 else ''}"
                return {
                    "action": "set_clock_timer",
                    "target": "none",
                    "parameter": str(total_minutes),
                    "spoken_response": f"Setting a {dur_str} timer in Clock, boss."
                }

        # Skill 6b: Target Destination Countdown Timer
        if "countdown" in clean_text or "remaining" in clean_text or "timer" in clean_text:
            # Try matching 12-hour AM/PM format first
            time_match = re.search(r'(\d{1,2})(?:[:.\s](\d{2}))?\s*(a\.?m\.?|p\.?m\.?)', clean_text, re.IGNORECASE)
            if time_match:
                hr = time_match.group(1)
                mn = time_match.group(2) or "00"
                period = time_match.group(3).replace('.', '').upper()
                target_time = f"{hr}:{mn} {period}"
                return {
                    "action": "countdown_timer",
                    "target": "none",
                    "parameter": target_time,
                    "spoken_response": f"Calculating remaining time until {target_time}, boss."
                }
            # Fallback to 24-hour HH:MM format
            time_match_24 = re.search(r'(\d{1,2}):(\d{2})', clean_text)
            if time_match_24:
                target_time = time_match_24.group(0)
                return {
                    "action": "countdown_timer",
                    "target": "none",
                    "parameter": target_time,
                    "spoken_response": f"Calculating remaining time until {target_time}, boss."
                }

        websites = {
            "youtube": "https://www.youtube.com",
            "google": "https://www.google.com",
            "gmail": "https://mail.google.com",
            "facebook": "https://www.facebook.com",
            "github": "https://www.github.com",
            "zenflow": "https://preview--difference.lovable.app/",
            "zen": "https://preview--difference.lovable.app/",
            "flow": "https://preview--difference.lovable.app/",
            "zenf": "https://preview--difference.lovable.app/",
            "zflo": "https://preview--difference.lovable.app/",
            "zenfl": "https://preview--difference.lovable.app/",
            "flowzen": "https://preview--difference.lovable.app/",
            "zen_flow": "https://preview--difference.lovable.app/",
            "zen-flow": "https://preview--difference.lovable.app/",
            "znflow": "https://preview--difference.lovable.app/",
            "zen flow": "https://preview--difference.lovable.app/",
        }

        # Case 1: APP / BROWSER LAUNCHES (Commands starting with open/launch)
        if text.startswith("open ") or text.startswith("launch "):
            app_query = text.replace("open ", "", 1).replace("launch ", "", 1).strip()
            # Strip trailing/leading punctuation Whisper adds (e.g. "notepad." -> "notepad")
            app_query = re.sub(r'[^\w\s]', '', app_query).strip()

            # ── COMPOUND NOTEPAD COMMANDS ────────────────────────────────────────
            # Detect: "open notepad and type X" / "open notepad and write X"
            _notepad_names = ["notepad", "notes"]
            if any(app_query.startswith(_nw) for _nw in _notepad_names):
                for _type_kw in ["and type ", "and write ", "and enter "]:
                    if _type_kw in app_query:
                        _raw_text = app_query.split(_type_kw, 1)[1].strip().strip('"\'')
                        return {
                            "action": "launch_app",
                            "target": "notepad",
                            "parameter": f"type:{_raw_text}",
                            "spoken_response": "Opening Notepad and typing your message right away, boss."
                        }

            # ── COMPOUND CALCULATOR COMMANDS ─────────────────────────────────────
            # Detect: "open calculator and calculate X" / "open calc and compute X"
            _calc_names = ["calculator", "calc"]
            for _calc_nm in _calc_names:
                if app_query.startswith(_calc_nm):
                    for _action_kw in ["and calculate ", "and compute ", "and solve ", "and perform "]:
                        if _action_kw in app_query:
                            _expr_raw = app_query.split(_action_kw, 1)[1].strip()
                            # Remove trailing context like "in the calculator"
                            _expr_raw = re.sub(
                                r'\s*(in the calculator|in calculator|on the calculator|on it)\s*$',
                                '', _expr_raw, flags=re.IGNORECASE
                            ).strip()
                            return {
                                "action": "calculator_compute",
                                "target": "calculator",
                                "parameter": _expr_raw,
                                "spoken_response": "Opening Calculator and computing the result, boss."
                            }
                    break  # found the calc name — stop checking

            # ── COMPOUND BROWSER SEARCH COMMANDS ─────────────────────────────────────
            # Detect: "open chrome and search X", "open brave browser and search X", etc.
            # Runs BEFORE the generic browser lookup so the search query is extracted
            # cleanly rather than passing junk to Skill 7's text-replacement chain.
            _browser_names = [
                "operagx", "opera gx", "opera", "chrome", "firefox",
                "edge", "msedge", "brave", "safari", "browser"
            ]
            _search_prefixes = ["and search ", "and look up ", "and google "]
            for _search_prefix in _search_prefixes:
                if _search_prefix in app_query:
                    # Extract the raw browser part (before the search keyword)
                    _browser_part = app_query.split(_search_prefix)[0].strip()
                    # Normalise: strip "browser" suffix, resolve to canonical name
                    _browser_part = _browser_part.replace(" browser", "").strip()
                    _resolved = "msedge" if _browser_part == "edge" else _browser_part
                    if _resolved in _browser_names or _browser_part in _browser_names:
                        _search_query = app_query.split(_search_prefix, 1)[1].strip().strip('"\'')
                        _display_br = "Opera GX" if "gx" in _resolved.lower() else _resolved.capitalize()
                        return {
                            "action": "launch_app",
                            "target": _resolved,
                            "parameter": _search_query,
                            "spoken_response": f"Opening {_display_br} and searching for {_search_query}, boss."
                        }

            # Clean generic "browser" or "browser app" suffix if opening a browser directly
            # e.g., "brave browser" -> "brave", but "youtube in browser" -> do not strip "browser" here
            for suffix in [" browser", " app"]:
                if app_query.endswith(suffix):
                    prefix = app_query[:-len(suffix)].strip()
                    words = prefix.split()
                    last_word = words[-1] if words else ""
                    if last_word in ["chrome", "firefox", "edge", "msedge", "opera", "brave", "safari", "browser", "operagx", "opera gx", "gx"]:
                        app_query = prefix
            
            # 1a. If opening a known browser directly
            if app_query in ["chrome", "firefox", "edge", "msedge", "opera", "brave", "safari", "browser", "operagx", "opera gx"]:
                target_browser = "msedge" if app_query == "edge" else app_query
                display_name = "Opera GX" if "gx" in target_browser.lower() else (
                               "Chrome" if target_browser == "browser" else target_browser.capitalize())
                return {
                    "action": "launch_app",
                    "target": target_browser,
                    "parameter": "none",
                    "spoken_response": f"Opening {display_name} browser, boss."
                }
                
            # 1b. If opening a known website directly (e.g. "open youtube in brave browser")
            clean_app_query = app_query
            for b in ["operagx", "opera gx", "opera", "chrome", "firefox", "edge", "msedge", "brave", "safari", "browser"]:
                for suffix in [" browser", ""]:
                    term_with_suffix = b + suffix
                    for prep in [" in ", " on ", " using ", " with ", " via ", " to "]:
                        if prep + term_with_suffix in clean_app_query:
                            clean_app_query = clean_app_query.split(prep)[0].strip()
                            break
            
            if clean_app_query in websites:
                display_browser = "Opera GX" if "gx" in normalized_browser.lower() else (
                                  "Chrome" if normalized_browser == "browser" else normalized_browser.capitalize())
                display_name = clean_app_query.capitalize()
                zenflow_variants = {"zen", "flow", "zenf", "zflo", "zenfl", "zenflow", "flowzen", "zen_flow", "zen-flow", "znflow", "zen flow"}
                if clean_app_query in zenflow_variants:
                    display_name = "Zenflow"
                return {
                    "action": "launch_app",
                    "target": normalized_browser,
                    "parameter": websites[clean_app_query],
                    "spoken_response": f"Opening {display_name} in {display_browser}, boss."
                }

            # 1c. Windows Native Apps (e.g. "open notepad", "open calculator")
            apps = {
                "notepad":        "notepad",
                "notes":          "notepad",
                "calculator":     "calculator",
                "calc":           "calculator",
                "command prompt": "cmd",
                "cmd":            "cmd",
                "explorer":       "explorer",
                "fileexplorer":   "explorer",
                "file explorer":  "explorer",
                "task manager":   "task manager",
                # UWP apps
                "clock":          "clock",
                "alarms":         "alarms",
                "alarm":          "alarms",
                "timer":          "timer",
                "whatsapp":       "whatsapp",
            }
            if clean_app_query in apps:
                target_app = apps[clean_app_query]
                return {
                    "action": "launch_app",
                    "target": target_app,
                    "parameter": "none",
                    "spoken_response": f"Opening {clean_app_query.capitalize()} right away, boss."
                }
                
            # 1d. Handle compound app launches with quotes or jokes (e.g. "open notepad and tell me a joke")
            words = clean_app_query.split()
            first_word = words[0] if words else ""
            if first_word in apps or first_word in ["operagx", "opera gx", "opera", "chrome", "firefox", "edge", "msedge", "brave", "safari", "browser"]:
                target_app = "msedge" if first_word == "edge" else apps.get(first_word, first_word)
                spoken = f"Opening {first_word.capitalize()} browser, sir."
                if "quote" in clean_app_query:
                    spoken = f"Right away, sir. Opening {first_word.capitalize()}. As requested, here is your quote: 'Success is not final, failure is not fatal: it is the courage to continue that counts.'"
                elif "joke" in clean_app_query:
                    spoken = f"Opening {first_word.capitalize()}, sir. And here is a joke: Why don't scientists trust atoms? Because they make up everything!"
                
                return {
                    "action": "launch_app",
                    "target": target_app,
                    "parameter": "none",
                    "spoken_response": spoken
                }

        # Case 2: YOUTUBE / PLAY COMMANDS
        if "play " in clean_text or "youtube" in clean_text:
            song_query = ""
            if "play the song " in clean_text:
                song_query = clean_text.split("play the song ")[-1]
            elif "play " in clean_text:
                song_query = clean_text.split("play ")[-1]
            else:
                song_query = clean_text
                
            # Strip residual terms to extract pure video name
            song_query = song_query.replace("on youtube", "").replace("in youtube", "").replace("youtube", "").strip()
            
            if song_query:
                display_browser = "Chrome" if normalized_browser == "browser" else normalized_browser.capitalize()
                return {
                    "action": "launch_app",
                    "target": normalized_browser,
                    "parameter": f"youtube {song_query}",
                    "spoken_response": f"Right away, boss. Playing {song_query} from YouTube in {display_browser}."
                }

        # Case 3: WEB SEARCH COMMANDS (e.g. "search for tomorrow's weather")
        search_prefixes = ["search for ", "search ", "google ", "look up "]
        for prefix in search_prefixes:
            if clean_text.startswith(prefix):
                search_query = clean_text[len(prefix):].strip()
                if search_query:
                    display_browser = "Chrome" if normalized_browser == "browser" else normalized_browser.capitalize()
                    return {
                        "action": "launch_app",
                        "target": normalized_browser,
                        "parameter": search_query,
                        "spoken_response": f"Indeed, boss. Opening your {display_browser} and searching for {search_query}."
                    }

        # Case 4: VOLUME / SYSTEM CONTROLS
        if "volume up" in text or "increase volume" in text:
            return {
                "action": "system_control",
                "target": "volume_up",
                "parameter": "none",
                "spoken_response": "Increasing volume, boss."
            }
        elif "volume down" in text or "decrease volume" in text:
            return {
                "action": "system_control",
                "target": "volume_down",
                "parameter": "none",
                "spoken_response": "Decreasing volume, boss."
            }
        elif "mute" in text:
            return {
                "action": "system_control",
                "target": "mute",
                "parameter": "none",
                "spoken_response": "Muting audio channels, boss."
            }

        return intent

