import os
import requests
import time
from datetime import datetime
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env", ".env"), override=False)
load_dotenv(override=False)  # Fallback to standard .env

class WeatherAgent:
    SERVICE_ERROR = "Sorry boss, I couldn't retrieve that information right now."

    def __init__(self):
        # Cache for city coordinates: city_clean -> (latitude, longitude, resolved_name)
        self._geo_cache = {}
        
        # Cache for weather forecasts: city_clean -> (timestamp, forecast_data)
        # We keep the forecast cache valid for 60 seconds.
        self._forecast_cache = {}
        self._cache_duration_seconds = 60
        
        # WMO Weather interpretation codes mapping
        self._wmo_codes = {
            0: "Clear sky",
            1: "Mainly clear",
            2: "Partly cloudy",
            3: "Overcast",
            45: "Fog",
            48: "Depositing rime fog",
            51: "Light drizzle",
            53: "Moderate drizzle",
            55: "Dense drizzle",
            56: "Light freezing drizzle",
            57: "Dense freezing drizzle",
            61: "Slight rain",
            63: "Moderate rain",
            65: "Heavy rain",
            66: "Light freezing rain",
            67: "Heavy freezing rain",
            71: "Slight snow fall",
            73: "Moderate snow fall",
            75: "Heavy snow fall",
            77: "Snow grains",
            80: "Slight rain showers",
            81: "Moderate rain showers",
            82: "Violent rain showers",
            85: "Slight snow showers",
            86: "Heavy snow showers",
            95: "Thunderstorm",
            96: "Thunderstorm with slight hail",
            99: "Thunderstorm with heavy hail"
        }

    def _robust_get(self, url: str, params: dict = None, timeout: int = 10, retries: int = 3):
        """
        Performs a GET request with automatic retries on timeouts or connection errors.
        """
        for attempt in range(retries):
            try:
                response = requests.get(url, params=params, timeout=timeout)
                response.raise_for_status()
                return response
            except (requests.exceptions.Timeout, requests.exceptions.RequestException) as e:
                if attempt == retries - 1:
                    raise e
                time.sleep(1)

    def _get_coordinates(self, city: str):
        """
        Retrieves (latitude, longitude, resolved_name) for a given city name.
        Uses a dictionary cache to avoid redundant API requests.
        """
        city_clean = city.strip().lower()
        if city_clean in self._geo_cache:
            return self._geo_cache[city_clean]

        url = os.getenv("URL_WEATHER")
        params = {
            "name": city.strip(),
            "count": 1,
            "language": "en",
            "format": "json"
        }

        try:
            response = self._robust_get(url, params=params)
            data = response.json()
            
            if "results" in data and len(data["results"]) > 0:
                result = data["results"][0]
                lat = result.get("latitude")
                lon = result.get("longitude")
                resolved_name = result.get("name", city.strip().title())
                
                if lat is not None and lon is not None:
                    coords = (lat, lon, resolved_name)
                    self._geo_cache[city_clean] = coords
                    return coords
            
            return None
        except requests.exceptions.Timeout:
            raise requests.exceptions.Timeout(f"Geocoding service timed out for '{city}'.")
        except Exception as e:
            raise RuntimeError(f"Error fetching coordinates for '{city}': {str(e)}")

    def _get_forecast(self, city: str):
        """
        Retrieves the weather forecast JSON for the given city.
        Uses a short-lived cache (60 seconds) to avoid rate limits and minimize latency.
        """
        city_clean = city.strip().lower()
        now = time.time()
        
        # Check cache
        if city_clean in self._forecast_cache:
            cache_time, data = self._forecast_cache[city_clean]
            if now - cache_time < self._cache_duration_seconds:
                return data, data.get("resolved_name", city.strip().title())
                
        # Cache miss - fetch coordinates first
        coords = self._get_coordinates(city)
        if not coords:
            return None, None
            
        lat, lon, resolved_name = coords
        
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code",
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,sunrise,sunset",
            "timezone": "auto"
        }
        
        try:
            response = self._robust_get(url, params=params)
            data = response.json()
            
            # Store resolved_name in the data for easy retrieval
            data["resolved_name"] = resolved_name
            
            # Save to cache
            self._forecast_cache[city_clean] = (now, data)
            return data, resolved_name
        except requests.exceptions.Timeout:
            raise requests.exceptions.Timeout("Weather service timed out while fetching forecast data.")
        except Exception as e:
            raise RuntimeError(f"Failed to fetch forecast from Open-Meteo: {str(e)}")

    def _format_time(self, iso_datetime_str: str) -> str:
        """
        Formats an ISO datetime string like '2026-06-11T05:41'
        into a clean, human-readable local time format like '5:41 AM'.
        """
        try:
            # Open-Meteo returns ISO format like 'YYYY-MM-DDTHH:MM'
            time_part = iso_datetime_str.split('T')[1]
            time_obj = datetime.strptime(time_part, "%H:%M")
            hour = time_obj.hour
            minute = time_obj.minute
            
            ampm = "AM" if hour < 12 else "PM"
            hour_12 = hour % 12
            if hour_12 == 0:
                hour_12 = 12
                
            return f"{hour_12}:{minute:02d} {ampm}"
        except Exception:
            # Fallback to original string if parsing fails
            return iso_datetime_str

    def get_temperature(self, city: str) -> str:
        """
        Returns today's temperature for the city as a clean text string.
        """
        try:
            data, resolved_name = self._get_forecast(city)
            if not data:
                return self.SERVICE_ERROR
            temp = data.get("current", {}).get("temperature_2m")
            if temp is None:
                return self.SERVICE_ERROR
            return f"The current temperature in {resolved_name} is {round(temp)} degrees Celsius, boss."
        except Exception:
            return self.SERVICE_ERROR

    def get_max_temperature(self, city: str) -> str:
        """
        Returns today's maximum temperature for the city as a clean text string.
        """
        try:
            data, resolved_name = self._get_forecast(city)
            if not data:
                return self.SERVICE_ERROR
            max_temp_list = data.get("daily", {}).get("temperature_2m_max", [])
            if not max_temp_list:
                return self.SERVICE_ERROR
            return f"The maximum temperature in {resolved_name} today is {round(max_temp_list[0])} degrees Celsius, boss."
        except Exception:
            return self.SERVICE_ERROR

    def get_min_temperature(self, city: str) -> str:
        """
        Returns today's minimum temperature for the city as a clean text string.
        """
        try:
            data, resolved_name = self._get_forecast(city)
            if not data:
                return self.SERVICE_ERROR
            min_temp_list = data.get("daily", {}).get("temperature_2m_min", [])
            if not min_temp_list:
                return self.SERVICE_ERROR
            return f"The minimum temperature in {resolved_name} today is {round(min_temp_list[0])} degrees Celsius, boss."
        except Exception:
            return self.SERVICE_ERROR

    def get_sunrise(self, city: str) -> str:
        """
        Returns today's sunrise time for the city as a clean text string.
        """
        try:
            data, resolved_name = self._get_forecast(city)
            if not data:
                return self.SERVICE_ERROR
            sunrise_list = data.get("daily", {}).get("sunrise", [])
            if not sunrise_list:
                return self.SERVICE_ERROR
            formatted_sunrise = self._format_time(sunrise_list[0])
            return f"Today's sunrise in {resolved_name} is at {formatted_sunrise}, boss."
        except Exception:
            return self.SERVICE_ERROR

    def get_sunset(self, city: str) -> str:
        """
        Returns today's sunset time for the city as a clean text string.
        """
        try:
            data, resolved_name = self._get_forecast(city)
            if not data:
                return self.SERVICE_ERROR
            sunset_list = data.get("daily", {}).get("sunset", [])
            if not sunset_list:
                return self.SERVICE_ERROR
            formatted_sunset = self._format_time(sunset_list[0])
            return f"Today's sunset in {resolved_name} is at {formatted_sunset}, boss."
        except Exception:
            return self.SERVICE_ERROR

    def get_wind_speed(self, city: str) -> str:
        """
        Returns the current wind speed of the city as a clean text string.
        """
        try:
            data, resolved_name = self._get_forecast(city)
            if not data:
                return self.SERVICE_ERROR
            wind_speed = data.get("current", {}).get("wind_speed_10m")
            if wind_speed is None:
                return self.SERVICE_ERROR
            return f"The current wind speed in {resolved_name} is {wind_speed} km/h, boss."
        except Exception:
            return self.SERVICE_ERROR

    def get_rain_probability(self, city: str) -> str:
        """
        Returns today's rain probability for the city as a clean text string.
        """
        try:
            data, resolved_name = self._get_forecast(city)
            if not data:
                return self.SERVICE_ERROR
            rain_prob_list = data.get("daily", {}).get("precipitation_probability_max", [])
            if not rain_prob_list:
                return self.SERVICE_ERROR
            prob = round(rain_prob_list[0])
            return f"The rain probability in {resolved_name} today is {prob} percent, boss."
        except Exception:
            return self.SERVICE_ERROR

    def get_weather_summary(self, city: str) -> str:
        """
        Returns a full weather summary for the city.
        """
        try:
            data, resolved_name = self._get_forecast(city)
            if not data:
                return self.SERVICE_ERROR
            
            # Extract current data
            current_data = data.get("current", {})
            temp = current_data.get("temperature_2m")
            humidity = current_data.get("relative_humidity_2m")
            wind_speed = current_data.get("wind_speed_10m")
            wmo_code = current_data.get("weather_code")
            
            # Extract daily data
            daily_data = data.get("daily", {})
            max_temp_list = daily_data.get("temperature_2m_max", [])
            min_temp_list = daily_data.get("temperature_2m_min", [])
            rain_probability_list = daily_data.get("precipitation_probability_max", [])
            sunrise_list = daily_data.get("sunrise", [])
            sunset_list = daily_data.get("sunset", [])
            
            # Check for any missing values
            if (temp is None or wind_speed is None or wmo_code is None or 
                not max_temp_list or not min_temp_list or not rain_probability_list or
                not sunrise_list or not sunset_list):
                return self.SERVICE_ERROR
            
            # Map weather condition
            condition = self._wmo_codes.get(wmo_code, "Unknown weather conditions")
            
            # Format times
            formatted_sunrise = self._format_time(sunrise_list[0])
            formatted_sunset = self._format_time(sunset_list[0])
            rain_probability = round(rain_probability_list[0])
            humidity_text = f" Humidity is {round(humidity)} percent." if humidity is not None else ""
            
            # Build full summary
            return (
                f"Weather summary for {resolved_name}: The current condition is {condition.lower()}. "
                f"Current temperature is {round(temp)} degrees Celsius, with a maximum of {round(max_temp_list[0])} and a minimum of {round(min_temp_list[0])} degrees Celsius. "
                f"Rain probability today is {rain_probability} percent. "
                f"Sunrise is at {formatted_sunrise} and sunset is at {formatted_sunset}. "
                f"Wind speed is {wind_speed} km/h.{humidity_text}"
            )
            
        except requests.exceptions.Timeout:
            return self.SERVICE_ERROR
        except Exception:
            return self.SERVICE_ERROR
 
if __name__ == "__main__":
    weather = WeatherAgent()
    print(weather.get_weather_summary("Bengaluru"))
