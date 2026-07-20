import os
import requests
import time
import env_loader

class DictionaryAgent:
    def __init__(self):
        # Cache to store looked-up words: word_clean -> JSON_data or None (if not found)
        self._word_cache = {}

    def _robust_get(self, url: str, timeout: int = 10, retries: int = 3):
        """
        Performs a GET request with automatic retries on timeouts or connection errors.
        """
        for attempt in range(retries):
            try:
                response = requests.get(url, timeout=timeout)
                return response
            except (requests.exceptions.Timeout, requests.exceptions.RequestException) as e:
                if attempt == retries - 1:
                    raise e
                time.sleep(1)

    def _get_word_data(self, word: str):
        """
        Retrieves the API response JSON for a given word.
        Uses a session-lifetime dictionary cache to avoid redundant API queries.
        """
        word_clean = word.strip().lower()
        if not word_clean:
            raise ValueError("Empty word provided")

        if word_clean in self._word_cache:
            data = self._word_cache[word_clean]
            if data is None:
                # Word was previously looked up and not found (404)
                raise ValueError("Word not found")
            return data

        url_template = os.getenv("URL_DICTIONARY") or "https://api.dictionaryapi.dev/api/v2/entries/en/{word_clean}"
        url = url_template.format(word_clean=word_clean)
        try:
            response = self._robust_get(url)
            
            if response.status_code == 404:
                # Cache the negative lookup to prevent spamming invalid words
                self._word_cache[word_clean] = None
                raise ValueError("Word not found")
                
            response.raise_for_status()
            data = response.json()
            
            if isinstance(data, list) and len(data) > 0:
                self._word_cache[word_clean] = data
                return data
            else:
                self._word_cache[word_clean] = None
                raise ValueError("Word not found")
                
        except (requests.exceptions.Timeout, requests.exceptions.RequestException):
            raise ConnectionError("Sorry boss, that service is currently unavailable.")

    def get_definition(self, word: str) -> str:
        """
        Returns the first definition of the first meaning of the word.
        Optimized for voice output (keeps only the first sentence).
        """
        try:
            data = self._get_word_data(word)
            if not data:
                return "Sorry, I could not find a definition for that word."
                
            first_entry = data[0]
            meanings = first_entry.get("meanings", [])
            if not meanings:
                return "Sorry, I could not find a definition for that word."
                
            first_meaning = meanings[0]
            definitions = first_meaning.get("definitions", [])
            if not definitions:
                return "Sorry, I could not find a definition for that word."
                
            raw_definition = definitions[0].get("definition", "").strip()
            if not raw_definition:
                return "Sorry, I could not find a definition for that word."
                
            # Sentence extraction logic for concise text-to-speech
            if ". " in raw_definition:
                first_sentence = raw_definition.split(". ")[0].strip()
            else:
                first_sentence = raw_definition.strip()
                if first_sentence.endswith("."):
                    first_sentence = first_sentence[:-1].strip()
            
            # Ensure it ends with exactly one period
            if not first_sentence.endswith("."):
                first_sentence += "."
                
            return first_sentence
            
        except ValueError:
            return "Sorry, I could not find a definition for that word."
        except ConnectionError:
            return "Sorry boss, that service is currently unavailable."
        except Exception:
            return "Sorry boss, I couldn't retrieve that information right now."

    def get_pronunciation(self, word: str) -> str:
        """
        Returns the phonetic transcription of the word (e.g. '/səʊl/').
        Falls back to '/word/' if no phonetic spelling is listed.
        """
        try:
            data = self._get_word_data(word)
            if not data:
                return "Sorry, I could not find a definition for that word."
                
            first_entry = data[0]
            
            # Check top-level phonetic key
            phonetic = first_entry.get("phonetic")
            
            # If not found, check the phonetics list
            if not phonetic:
                phonetics = first_entry.get("phonetics", [])
                for p in phonetics:
                    if p.get("text"):
                        phonetic = p.get("text")
                        break
                        
            # Fallback to standard word representation in slashes if no phonetic text is available
            if not phonetic:
                phonetic = f"/{word.strip().lower()}/"
                
            return phonetic
            
        except ValueError:
            return "Sorry, I could not find a definition for that word."
        except ConnectionError:
            return "Sorry boss, that service is currently unavailable."
        except Exception:
            return "Sorry boss, I couldn't retrieve that information right now."

    def get_part_of_speech(self, word: str) -> str:
        """
        Returns the part of speech of the first meaning of the word (e.g. 'noun').
        """
        try:
            data = self._get_word_data(word)
            if not data:
                return "Sorry, I could not find a definition for that word."
                
            first_entry = data[0]
            meanings = first_entry.get("meanings", [])
            if not meanings:
                return "Sorry, I could not find a definition for that word."
                
            part_of_speech = meanings[0].get("partOfSpeech", "").strip().lower()
            if not part_of_speech:
                return "Sorry, I could not find a definition for that word."
                
            return part_of_speech
            
        except ValueError:
            return "Sorry, I could not find a definition for that word."
        except ConnectionError:
            return "Sorry boss, that service is currently unavailable."
        except Exception:
            return "Sorry boss, I couldn't retrieve that information right now."

    def get_dictionary_summary(self, word: str) -> str:
        """
        Returns a clean, voice-friendly summary of the word suitable for Panda TTS.
        Format: "Word is a part_of_speech. It means definition. Pronunciation is word."
        """
        try:
            data = self._get_word_data(word)
            if not data:
                return "Sorry, I could not find a definition for that word."
                
            first_entry = data[0]
            meanings = first_entry.get("meanings", [])
            if not meanings:
                return "Sorry, I could not find a definition for that word."
                
            part_of_speech = meanings[0].get("partOfSpeech", "").strip().lower()
            
            # Fetch the definition and make sure it has the first letter lowercased (for flowing in sentence)
            definition_text = self.get_definition(word)
            
            # If the definition returned is an error message, propagate it
            if definition_text.startswith("Sorry, I could not") or definition_text.startswith("Sorry boss"):
                return definition_text
                
            clean_def = definition_text.strip()
            if clean_def.endswith("."):
                clean_def = clean_def[:-1].strip()
                
            if clean_def:
                clean_def = clean_def[0].lower() + clean_def[1:]
                
            # Build clean voice summary
            return f"{word.strip().title()} is a {part_of_speech}. It means {clean_def}. Pronunciation is {word.strip().lower()}."
            
        except ValueError:
            return "Sorry, I could not find a definition for that word."
        except ConnectionError:
            return "Sorry boss, that service is currently unavailable."
        except Exception:
            return "Sorry boss, I couldn't retrieve that information right now."

if __name__ == "__main__":
    dictionary = DictionaryAgent()
    print(dictionary.get_dictionary_summary("workaholic"))
