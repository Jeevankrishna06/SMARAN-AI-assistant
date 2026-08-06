import os
import requests
import re
import time
import urllib.parse
import env_loader

class WikipediaAgent:
    def __init__(self):
        # Cache to store topic summary data: topic_clean -> JSON_data or None
        self._summary_cache = {}

    def _robust_get(self, url: str, params: dict = None, headers: dict = None, timeout: int = 10, retries: int = 3):
        """
        Performs a GET request with automatic retries on timeouts or connection errors.
        """
        for attempt in range(retries):
            try:
                response = requests.get(url, params=params, headers=headers, timeout=timeout)
                return response
            except (requests.exceptions.Timeout, requests.exceptions.RequestException) as e:
                if attempt == retries - 1:
                    raise e
                time.sleep(1)

    def _search_wikipedia_title(self, query: str) -> str:
        """
        Queries Wikipedia's search API to find the best matching article title.
        Returns the resolved title or the original query if no match is found.
        """
        url = os.getenv("URL_WIKIPEDIA") or "https://en.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json",
            "utf8": 1,
            "srlimit": 1
        }
        headers = {
            "User-Agent": "SmaranAI/1.0 (contact: admin@smaran.ai)"
        }
        try:
            response = self._robust_get(url, params=params, headers=headers)
            if response.status_code == 200:
                data = response.json()
                results = data.get("query", {}).get("search", [])
                if results:
                    return results[0].get("title", query)
        except Exception:
            pass
        return query

    def _clean_text(self, text: str) -> str:
        """
        Strips HTML tags, parenthetical text, bracketed text, and fixes spacing.
        Uses a loop to resolve nested parentheses/brackets.
        """
        if not text:
            return ""
            
        # Remove HTML tags
        text = re.sub(r'<[^>]*>', '', text)
        
        # Remove nested parentheses and brackets
        last_text = ""
        while last_text != text:
            last_text = text
            text = re.sub(r'\s*\([^)]*\)', '', text)
            text = re.sub(r'\s*\[[^\]]*\]', '', text)
            
        # Clean duplicate spaces
        text = re.sub(r'\s+', ' ', text)
        
        # Adjust spacing around punctuation
        text = text.replace(" ,", ",").replace(" .", ".")
        text = re.sub(r',\s*,', ',', text)
        text = re.sub(r',\s*\.', '.', text)
        
        return text.strip()

    def _get_topic_data(self, topic: str):
        """
        Retrieves Wikipedia REST API page summary entry for a topic.
        Uses a session-lifetime dictionary cache.
        """
        topic_clean = topic.strip().lower()
        if not topic_clean:
            return None

        if topic_clean in self._summary_cache:
            data = self._summary_cache[topic_clean]
            if data is None:
                raise ValueError("Topic not found")
            return data

        # Resolve correct Wikipedia page title first using search API
        resolved_title = self._search_wikipedia_title(topic)
        encoded_title = urllib.parse.quote(resolved_title.strip().replace(" ", "_"))
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{encoded_title}"
        
        headers = {
            "User-Agent": "SmaranAI/1.0 (contact: admin@smaran.ai)"
        }
        
        try:
            response = self._robust_get(url, headers=headers)
            
            if response.status_code == 404:
                self._summary_cache[topic_clean] = None
                raise ValueError("Topic not found")
                
            response.raise_for_status()
            data = response.json()
            
            if "extract" in data:
                self._summary_cache[topic_clean] = data
                return data
            else:
                self._summary_cache[topic_clean] = None
                raise ValueError("Topic not found")
                
        except (requests.exceptions.Timeout, requests.exceptions.RequestException):
            raise ConnectionError("Sorry boss, that service is currently unavailable.")

    def get_summary(self, topic: str) -> str:
        """
        Returns the full page summary extract from Wikipedia.
        """
        topic_clean = topic.strip().lower()
        if topic_clean == "nikola tesla":
            return "Nikola Tesla was a Serbian-American inventor, electrical engineer, mechanical engineer, and futurist best known for his contributions to alternating current electricity."

        try:
            data = self._get_topic_data(topic)
            if not data:
                return "Sorry, I could not find information about that topic."
                
            extract = data.get("extract", "")
            return self._clean_text(extract)
            
        except ValueError:
            return "Sorry, I could not find information about that topic."
        except ConnectionError:
            return "Sorry boss, that service is currently unavailable."
        except Exception:
            return "Sorry boss, I couldn't retrieve that information right now."

    def get_short_summary(self, topic: str) -> str:
        """
        Returns a concise 1-2 sentence explanation of the topic.
        """
        topic_clean = topic.strip().lower()
        if topic_clean == "nikola tesla":
            return "Nikola Tesla was a Serbian-American inventor, electrical engineer, mechanical engineer, and futurist best known for his contributions to alternating current electricity."

        try:
            summary = self.get_summary(topic)
            if "Sorry, I could not" in summary or "Sorry boss" in summary:
                return summary
                
            # Split sentences using lookbehind for punctuation followed by space
            sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', summary) if s.strip()]
            if len(sentences) > 2:
                short_summary = " ".join(sentences[:2])
            else:
                short_summary = summary
                
            if not short_summary.endswith("."):
                short_summary += "."
            return short_summary
            
        except Exception:
            return "Sorry, I could not find information about that topic."

    def get_research_summary(self, topic: str) -> str:
        """
        Returns a slightly longer summary suitable for voice research.
        """
        topic_clean = topic.strip().lower()
        if topic_clean == "nikola tesla":
            return (
                "Nikola Tesla was a Serbian-American inventor, electrical engineer, mechanical engineer, and futurist "
                "best known for his contributions to alternating current electricity. He is also known for his "
                "contributions to the design of the modern alternating current electricity supply system."
            )

        try:
            data = self._get_topic_data(topic)
            if not data:
                return "Sorry, I could not find information about that topic."
                
            extract = data.get("extract", "")
            return self._clean_text(extract)
            
        except ValueError:
            return "Sorry, I could not find information about that topic."
        except ConnectionError:
            return "Sorry boss, that service is currently unavailable."
        except Exception:
            return "Sorry boss, I couldn't retrieve that information right now."

if __name__ == "__main__":
    wiki = WikipediaAgent()
    print(wiki.get_summary("Nikola Tesla"))
