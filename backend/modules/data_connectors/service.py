"""
Data Connectors — Service Layer
Unified service orchestrating both weather and grid clients.
"""

from backend.common.logger import logger as log
from backend.modules.data_connectors.weather import WeatherClient
from backend.modules.data_connectors.grid import GridClient
from backend.modules.data_connectors.schemas import WeatherResponse, GridDataResponse


class DataConnectorService:
    """Orchestrates data fetching for the entire Data Connectors module."""
    
    def __init__(self):
        self.weather_client = WeatherClient()
        self.grid_client = GridClient()
        log.info("DataConnectorService initialized.")
        
    def get_current_weather(self) -> WeatherResponse:
        """Fetches the current weather."""
        # Here we could easily add caching (e.g., redis or simple dict cache)
        # to avoid hitting Open-Meteo on every single request if needed.
        return self.weather_client.fetch_current_weather()
        
    def get_current_grid_state(self) -> GridDataResponse:
        """Fetches the current macro grid state."""
        return self.grid_client.fetch_current_grid_state()
