import os
import time
from dotenv import load_dotenv

# Path to the .env file is inside a folder named .env (c:\Users\HP\OneDrive\Desktop\Smaran-AI Assistant(AUTOMATION AGENT)\.env\.env)
dotenv_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
dotenv_file = os.path.join(dotenv_dir, ".env")
if os.path.exists(dotenv_file):
    load_dotenv(dotenv_file)
else:
    load_dotenv()

try:
    from google import genai
    from google.genai import types
    _GENAI_AVAILABLE = True
except ImportError:
    _GENAI_AVAILABLE = False

# ------------------------------------------------------------------ #
#  System Prompt                                                       #
# ------------------------------------------------------------------ #

_SYSTEM_PROMPT = """You are Smaran's Reasoning Agent — a concise, conversational AI assistant
embedded inside a voice assistant called Smaran.

Your role covers:
- Answering factual questions clearly
- Providing beginner-friendly explanations
- Making structured comparisons between two items
- Summarizing provided text
- Reasoning, recommendations, problem solving, productivity advice, and brainstorming

You are NOT responsible for:
- Weather information (handled by WeatherAgent)
- Dictionary definitions (handled by DictionaryAgent)
- News retrieval (handled by NewsAgent)
- Wikipedia lookups (handled by WikipediaAgent)

Response guidelines (CRITICAL — follow these strictly):
- Keep all valid responses between 250-300 words
- For cases where you don't understand or can't answer, respond with just 1-2 brief sentences like "I didn't understand that" or "Sorry, I'm not sure"
- Write in plain, conversational English suitable for text-to-speech
- Never use markdown, asterisks, bullet points, dashes, or code blocks unless
  the user explicitly asks for code
- Never begin with affirmations like "Sure!", "Great question!", "Absolutely!"
- Speak directly and naturally as if talking to a person
- End cleanly without filler like "I hope that helps" or "Let me know if..."
- Provide comprehensive, detailed explanations while staying within the word limit
"""

# ------------------------------------------------------------------ #
#  GeminiAgent                                                         #
# ------------------------------------------------------------------ #

class GeminiAgent:
    """
    Reasoning agent powered by Google Gemini 2.5 Flash.
    Requires the GEMINI_API_KEY environment variable to be set.
    """

    MODEL = "gemini-2.5-flash"

    def __init__(self):
        self._api_key = os.environ.get("GEMINI_API_KEY")
        self._client = None
        self._config = None

        if _GENAI_AVAILABLE and self._api_key:
            self._client = genai.Client(api_key=self._api_key)
            grounding_tool = types.Tool(
                google_search=types.GoogleSearch()
            )
            self._config = types.GenerateContentConfig(
                system_instruction=_SYSTEM_PROMPT,
                temperature=0.2,            # Factual, low-entropy responses
                max_output_tokens=1000,     # ~250-300 words with headroom
                tools=[grounding_tool]      # Enable Google Search grounding!
            )

    # ------------------------------------------------------------------ #
    #  Internal Helpers                                                    #
    # ------------------------------------------------------------------ #

    def _check_ready(self):
        """Raises ValueError if the API key or SDK is missing."""
        if not _GENAI_AVAILABLE:
            raise ImportError(
                "google-genai package is not installed. "
                "Run: pip install google-genai"
            )
        if not self._api_key:
            raise ValueError(
                "Gemini API key is not set. "
                "Please set the GEMINI_API_KEY environment variable."
            )

    def _sanitize(self, text: str) -> str:
        """
        Strips common markdown artefacts that Gemini may produce
        even when instructed not to, for clean TTS output.
        """
        import re
        # Remove markdown links e.g. [Anchor](url)
        text = re.sub(r'\[.*?\]\(.*?\)', '', text)
        # Remove citation bracket numbers like [1], [2], [10]
        text = re.sub(r'\[\d+\]', '', text)
        # Remove bold/italic markers
        text = re.sub(r'\*{1,3}(.*?)\*{1,3}', r'\1', text)
        # Remove markdown headers
        text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
        # Remove horizontal rules
        text = re.sub(r'^[-_*]{3,}\s*$', '', text, flags=re.MULTILINE)
        # Collapse multiple blank lines to one
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

    def _call(self, prompt: str, retries: int = 2) -> str:
        """
        Core Gemini API call with lightweight retry logic.
        Returns the cleaned response text.
        """
        self._check_ready()

        last_error = None
        for attempt in range(retries):
            try:
                response = self._client.models.generate_content(
                    model=self.MODEL,
                    contents=prompt,
                    config=self._config
                )

                text = getattr(response, "text", None)
                if not text or not text.strip():
                    return "Sorry boss, I couldn't retrieve that information right now."

                return self._sanitize(text)

            except Exception as exc:
                last_error = exc
                if attempt < retries - 1:
                    time.sleep(1)

        # All retries exhausted
        err_str = str(last_error).lower()
        if "quota" in err_str or "rate" in err_str:
            return "Sorry boss, that service is currently unavailable."
        return "Sorry boss, that service is currently unavailable."

    def classify_route(self, query: str) -> str:
        """
        Classifies a router query without answering it.
        Returns one of: weather, dictionary, wikipedia, news, reasoning.
        """
        try:
            self._check_ready()
            config = types.GenerateContentConfig(
                system_instruction=(
                    "You are only a router classifier. Return exactly one label: "
                    "weather, dictionary, wikipedia, news, reasoning. No explanation."
                ),
                temperature=0,
                max_output_tokens=5,
            )
            response = self._client.models.generate_content(
                model=self.MODEL,
                contents=query.strip(),
                config=config
            )
            label = getattr(response, "text", "") or ""
            return label.strip().lower()
        except Exception:
            return "reasoning"

    # ------------------------------------------------------------------ #
    #  Public Methods                                                      #
    # ------------------------------------------------------------------ #

    def ask(self, query: str) -> str:
        """
        Returns a concise, factual answer to any general question.
        """
        if not query or not query.strip():
            return "I didn't understand that."
        try:
            self._check_ready()
            prompt = (
                f"Answer this question completely in 250-300 words, "
                f"no markdown, no bullet points:\n\n{query.strip()}"
            )
            return self._call(prompt)
        except (ValueError, ImportError):
            return "Sorry boss, that service is currently unavailable."
        except Exception:
            return "Sorry boss, that service is currently unavailable."

    def explain(self, topic: str) -> str:
        """
        Returns a beginner-friendly plain-English explanation of a topic.
        """
        if not topic or not topic.strip():
            return "Sorry, I didn't understand that."
        try:
            self._check_ready()
            prompt = (
                f"Explain '{topic.strip()}' in simple, beginner-friendly terms "
                f"in 250-300 words. Write conversationally, no markdown, no bullet points."
            )
            return self._call(prompt)
        except (ValueError, ImportError):
            return "Sorry boss, that service is currently unavailable."
        except Exception:
            return "Sorry boss, that service is currently unavailable."

    def compare(self, item1: str, item2: str) -> str:
        """
        Returns a structured but voice-friendly comparison of two items.
        """
        if not item1 or not item2:
            return "I need two items to compare."
        try:
            self._check_ready()
            prompt = (
                f"Compare '{item1.strip()}' and '{item2.strip()}' in plain English "
                f"in 250-300 words. Highlight key differences and when to choose each. "
                f"No markdown, no bullet points, write as flowing sentences."
            )
            return self._call(prompt)
        except (ValueError, ImportError):
            return "Sorry boss, that service is currently unavailable."
        except Exception:
            return "Sorry boss, that service is currently unavailable."

    def summarize(self, text: str) -> str:
        """
        Returns a concise, voice-friendly summary of the provided text.
        """
        if not text or not text.strip():
            return "I need some text to summarize."
        try:
            self._check_ready()
            prompt = (
                f"Summarize the following text in 250-300 words. "
                f"Write in plain English suitable for speaking aloud. "
                f"No markdown, no bullet points:\n\n{text.strip()}"
            )
            return self._call(prompt)
        except (ValueError, ImportError):
            return "Sorry boss, that service is currently unavailable."
        except Exception:
            return "Sorry boss, that service is currently unavailable."

    def handle(self, query: str) -> str:
        """
        General-purpose entry point for the future Intelligence Router.
        Handles any reasoning, recommendation, or explanation query.
        """
        if not query or not query.strip():
            return "I didn't understand that."
        try:
            self._check_ready()
            prompt = (
                f"Respond to the following request in plain English in 250-300 words. "
                f"Be helpful, direct, and conversational. No markdown, no bullet points:\n\n"
                f"{query.strip()}"
            )
            return self._call(prompt)
        except (ValueError, ImportError):
            return "Sorry boss, that service is currently unavailable."
        except Exception:
            return "Sorry boss, that service is currently unavailable."

    def query_with_history(self, user_text: str, history: list) -> str:
        """
        Intelligence Mode query — sends conversation history alongside the message
        so Gemini can maintain multi-turn context with Google Search grounding.
        """
        if not user_text or not user_text.strip():
            return "I didn't understand that."
        try:
            self._check_ready()
            
            # Convert history to Google GenAI format
            formatted_history = []
            for msg in history:
                role = "model" if msg.get("role") == "assistant" else "user"
                content = msg.get("content", "").strip()
                if content:
                    formatted_history.append({
                        "role": role,
                        "parts": [{"text": content}]
                    })
                    
            chat = self._client.chats.create(
                model=self.MODEL,
                config=self._config,
                history=formatted_history
            )
            
            response = chat.send_message(user_text)
            text = getattr(response, "text", None)
            if not text or not text.strip():
                return "Sorry boss, I couldn't retrieve that information right now."
                
            return self._sanitize(text)
        except Exception as exc:
            print(f"[GEMINI] Error in query_with_history: {exc}")
            raise exc



# ------------------------------------------------------------------ #
#  Quick Test Block                                                    #
# ------------------------------------------------------------------ #
if __name__ == "__main__":
    gemini = GeminiAgent()
    print("--- ask('What is recursion?') ---")
    print(gemini.ask("What is recursion?"))
    print()
    print("--- compare('Python', 'Java') ---")
    print(gemini.compare("Python", "Java"))
