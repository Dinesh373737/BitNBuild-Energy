"""
Data Connectors — Schemas
Pydantic models for the data received from external weather and grid APIs.
"""

from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class WeatherResponse(BaseModel):
    """Schema for current and forecasted weather data."""
    timestamp: datetime = Field(..., description="Time of the weather reading")
    temperature_c: float = Field(..., description="Temperature in Celsius")
    cloud_cover_percent: float = Field(..., ge=0.0, le=100.0, description="Cloud cover percentage (0-100)")
    wind_speed_kmh: float = Field(..., ge=0.0, description="Wind speed in km/h")
    solar_radiation_wm2: float = Field(0.0, ge=0.0, description="Solar radiation in W/m² (if available)")
    is_forecast: bool = Field(False, description="True if this is a future forecast, False if live")

    model_config = ConfigDict(from_attributes=True)


class GridDataResponse(BaseModel):
    """Schema for macro grid state (e.g., Karnataka State Grid)."""
    timestamp: datetime = Field(..., description="Time of the grid reading")
    total_demand_mw: float = Field(..., ge=0.0, description="Total grid demand in MW")
    total_generation_mw: float = Field(..., ge=0.0, description="Total grid generation in MW")
    solar_generation_mw: float = Field(0.0, ge=0.0, description="Solar generation in MW")
    wind_generation_mw: float = Field(0.0, ge=0.0, description="Wind generation in MW")
    grid_frequency_hz: float = Field(50.0, description="Grid frequency in Hz (typically 50Hz in India)")
    status: str = Field("NORMAL", description="Status of the grid (e.g., NORMAL, STRESSED, OUTAGE)")
    is_simulated: bool = Field(False, description="True if this is fallback/mock data, False if real API")

    model_config = ConfigDict(from_attributes=True)
