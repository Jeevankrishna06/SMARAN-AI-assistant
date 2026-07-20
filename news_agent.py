import os
import requests
import time
from dotenv import load_dotenv
load_dotenv()

class NewsAgent:
    """
    Fetches news headlines and topic-based searches using the GNews API.
    Requires the GNEWS_API_KEY environment variable to be set.
    """

    BASE_URL = os.getenv("BASE_URL_NEWS")

    def __init__(self):
        self._api_key = os.getenv("NEWS_API_KEY")
        if not self._api_key:
            raise ValueError(
                "News API key is not set. "
                "Please set the NEWS_API_KEY environment variable."
)

    # ------------------------------------------------------------------ #
    #  Internal Helpers                                                    #
    # ------------------------------------------------------------------ #

    def _robust_get(self, url: str, params: dict, timeout: int = 10,
                    retries: int = 3):
        """
        GET request with automatic retries on transient network errors.
        Raises ConnectionError after all retries are exhausted.
        """
        for attempt in range(retries):
            try:
                response = requests.get(url, params=params, timeout=timeout)
                return response
            except (requests.exceptions.Timeout,
                    requests.exceptions.RequestException) as exc:
                if attempt == retries - 1:
                    raise ConnectionError(
                        "Sorry boss, that service is currently unavailable."
                    ) from exc
                time.sleep(1)

    def _check_api_key(self):
        """Raises ValueError if the API key is not configured."""
        if not self._api_key:
            raise ValueError(
                "GNews API key is not set. "
                "Please set the GNEWS_API_KEY environment variable."
            )

    def _format_headlines(self, articles: list, label: str) -> str:
        """
        Converts a list of article dicts into a concise, voice-friendly string.
        Format:
            "Here are the latest [label]. [Title 1]. [Title 2]. [Title 3]."
        """
        if not articles:
            return "No recent news was found for that topic."

        # Keep only the first 3 headlines
        headlines = []
        for article in articles[:3]:
            title = article.get("title", "").strip()
            # Strip anything after a " - " source attribution
            if " - " in title:
                title = title.rsplit(" - ", 1)[0].strip()
            if title:
                # Make sure the title ends with a period for natural TTS flow
                if not title.endswith("."):
                    title += "."
                headlines.append(title)

        if not headlines:
            return "No recent news was found for that topic."

        return f"Here are the latest {label}. " + " ".join(headlines)

    # ------------------------------------------------------------------ #
    #  Public Methods                                                      #
    # ------------------------------------------------------------------ #

    def get_top_news(self) -> str:
        """
        Returns the top 3 current news headlines (general category, English).
        """
        try:
            self._check_api_key()

            params = {
                "category": "general",
                "lang": "en",
                "max": 3,
                "apikey": self._api_key
            }

            response = self._robust_get(
                f"{self.BASE_URL}/top-headlines", params
            )

            if response.status_code == 401:
                return "Sorry boss, that service is currently unavailable."
            if response.status_code == 403:
                return "Sorry boss, that service is currently unavailable."

            response.raise_for_status()
            data = response.json()
            articles = data.get("articles", [])

            return self._format_headlines(articles, "news headlines")

        except ValueError:
            return "Sorry boss, that service is currently unavailable."
        except ConnectionError:
            return "Sorry boss, that service is currently unavailable."
        except Exception:
            return "Sorry boss, that service is currently unavailable."

    def search_news(self, topic: str) -> str:
        """
        Returns the top 3 news headlines related to the given topic.
        Sorted by relevance.
        """
        if not topic or not topic.strip():
            return "No recent news was found for that topic."

        try:
            self._check_api_key()

            params = {
                "q": topic.strip(),
                "lang": "en",
                "max": 3,
                "sortby": "relevance",
                "apikey": self._api_key
            }

            response = self._robust_get(
                f"{self.BASE_URL}/search", params
            )

            if response.status_code in (401, 403):
                return "Sorry boss, that service is currently unavailable."

            response.raise_for_status()
            data = response.json()
            articles = data.get("articles", [])

            if not articles:
                return "No recent news was found for that topic."

            label = f"{topic.strip()} news"
            return self._format_headlines(articles, label)

        except ValueError:
            return "Sorry boss, that service is currently unavailable."
        except ConnectionError:
            return "Sorry boss, that service is currently unavailable."
        except Exception:
            return "Sorry boss, I couldn't retrieve that information right now."

    def get_latest_news(self, topic: str) -> str:
        """
        Returns the most recent 3 news headlines for the given topic.
        Sorted by publication date (newest first).
        """
        if not topic or not topic.strip():
            return "No recent news was found for that topic."

        try:
            self._check_api_key()

            params = {
                "q": topic.strip(),
                "lang": "en",
                "max": 3,
                "sortby": "publishedAt",
                "apikey": self._api_key
            }

            response = self._robust_get(
                f"{self.BASE_URL}/search", params
            )

            if response.status_code in (401, 403):
                return "Sorry boss, that service is currently unavailable."

            response.raise_for_status()
            data = response.json()
            articles = data.get("articles", [])

            if not articles:
                return "No recent news was found for that topic."

            label = f"{topic.strip()} news"
            return self._format_headlines(articles, label)

        except ValueError:
            return "Sorry boss, that service is currently unavailable."
        except ConnectionError:
            return "Sorry boss, that service is currently unavailable."
        except Exception:
            return "Sorry boss, I couldn't retrieve that information right now."


# ------------------------------------------------------------------ #
#  Quick Test Block                                                    #
# ------------------------------------------------------------------ #
if __name__ == "__main__":
    news = NewsAgent()
    print(news.get_top_news())
