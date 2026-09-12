"""
Data Connectors — Weather Client
Fetches real-time weather data from Open-Meteo API.
"""

import httpx
from datetime import datetime, timezone
from backend.common.config import settings
from backend.common.logger import logger as log
from backend.modules.data_connectors.schemas import WeatherResponse


class WeatherClient:
    """Client for fetching data from Open-Meteo."""
    
    def __init__(self):
        self.base_url = settings.OPEN_METEO_FORECAST_URL
        self.lat = settings.LATITUDE
        self.lon = settings.LONGITUDE
        self.timezone = settings.TIMEZONE
        
    def fetch_current_weather(self) -> WeatherResponse:
        """Fetches the current weather for the configured location."""
        
        # Open-Meteo requires latitude, longitude, and the specific variables we want
        params = {
            "latitude": self.lat,
            "longitude": self.lon,
            "current": "temperature_2m,cloud_cover,wind_speed_10m,shortwave_radiation",
            "timezone": self.timezone
        }
        
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(self.base_url, params=params)
                response.raise_for_status()
                data = response.json()
                
            current_data = data.get("current", {})
            
            # Open-Meteo provides timestamp in ISO format
            time_str = current_data.get("time")
            if time_str:
                dt = datetime.fromisoformat(time_str)
            else:
                dt = datetime.now(timezone.utc)
                
            return WeatherResponse(
                timestamp=dt,
                temperature_c=float(current_data.get("temperature_2m", 0.0)),
                cloud_cover_percent=float(current_data.get("cloud_cover", 0.0)),
                wind_speed_kmh=float(current_data.get("wind_speed_10m", 0.0)),
                solar_radiation_wm2=float(current_data.get("shortwave_radiation", 0.0)),
                is_forecast=False
            )
            
        except httpx.HTTPError as e:
            log.error(f"Failed to fetch weather from Open-Meteo: {e}")
            # Return a safe fallback if API fails
            return self._get_fallback_weather()
            
    def _get_fallback_weather(self) -> WeatherResponse:
        """Returns a safe fallback weather response if the external API is unreachable."""
        return WeatherResponse(
            timestamp=datetime.now(timezone.utc),
            temperature_c=25.0,
            cloud_cover_percent=20.0,
            wind_speed_kmh=10.0,
            solar_radiation_wm2=500.0,
            is_forecast=False
        )
