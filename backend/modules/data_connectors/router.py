"""
Data Connectors — API Router
Exposes endpoints to fetch external Weather and Grid data.
"""

from fastapi import APIRouter, Depends
from backend.modules.data_connectors.schemas import WeatherResponse, GridDataResponse
from backend.modules.data_connectors.service import DataConnectorService

router = APIRouter(prefix="/api/data", tags=["Data Connectors"])

def get_data_service() -> DataConnectorService:
    return DataConnectorService()

@router.get("/weather", response_model=WeatherResponse)
def get_weather(service: DataConnectorService = Depends(get_data_service)):
    """Retrieve the current weather conditions for the configured location."""
    return service.get_current_weather()

@router.get("/grid", response_model=GridDataResponse)
def get_grid(service: DataConnectorService = Depends(get_data_service)):
    """Retrieve the current macro-level grid status (e.g., Karnataka Grid)."""
    return service.get_current_grid_state()
