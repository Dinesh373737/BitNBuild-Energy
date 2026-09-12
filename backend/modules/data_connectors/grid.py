"""
Data Connectors — Grid Client
Generates simulated macro-level grid data (e.g., Karnataka State Grid).
"""

import math
from datetime import datetime, timezone
from backend.common.config import settings
from backend.common.logger import logger as log
from backend.modules.data_connectors.schemas import GridDataResponse


class GridClient:
    """Client for fetching or simulating macro Grid data."""
    
    def __init__(self):
        # We can configure real APIs here later if needed
        self.api_url = settings.KARNATAKA_GRID_API_URL
        self.api_key = settings.KARNATAKA_GRID_API_KEY
        
    def fetch_current_grid_state(self) -> GridDataResponse:
        """
        Fetches the current grid state.
        Currently falls back to a realistic mathematical simulation
        to avoid external dependencies for the macro grid.
        """
        if self.api_url:
            # Future placeholder for real API call
            log.info(f"Would fetch from {self.api_url}")
            
        return self._simulate_grid_data()
        
    def _simulate_grid_data(self) -> GridDataResponse:
        """
        Simulates realistic grid data for Karnataka (or similar state).
        Uses sine waves to create daily peaks and troughs.
        """
        now = datetime.now(timezone.utc)
        
        # Base demand in MW (e.g., 6000 MW base load)
        base_demand = 6000.0
        
        # Time of day factor (0.0 to 1.0)
        hour = now.hour + (now.minute / 60.0)
        
        # 1. Demand Curve: Peak around 19:00 (7 PM), dip around 03:00 (3 AM)
        # Shifted sine wave
        demand_fluctuation = math.sin(math.pi * (hour - 7) / 12) * 2000.0
        current_demand = base_demand + demand_fluctuation
        
        # 2. Solar Generation: Peak at 13:00 (1 PM), zero at night
        if 6 <= hour <= 18:
            solar_generation = math.sin(math.pi * (hour - 6) / 12) * 3000.0
        else:
            solar_generation = 0.0
            
        # 3. Wind Generation: Tends to be higher at night/evening, but add some randomness
        # Simple curve for simulation
        wind_generation = 1000.0 + math.sin(math.pi * hour / 12) * 500.0
        
        # 4. Total Generation: Always tries to match demand + a little buffer
        # In reality, generation must exactly match demand + losses.
        # We simulate a balanced grid here.
        total_generation = current_demand + 100.0
        
        # 5. Frequency: Around 50.0 Hz, fluctuates slightly based on demand vs generation
        frequency = 50.0 + (math.sin(hour * math.pi) * 0.05)
        
        status = "NORMAL"
        if current_demand > 8000.0:
            status = "STRESSED"

        return GridDataResponse(
            timestamp=now,
            total_demand_mw=round(current_demand, 2),
            total_generation_mw=round(total_generation, 2),
            solar_generation_mw=round(solar_generation, 2),
            wind_generation_mw=round(wind_generation, 2),
            grid_frequency_hz=round(frequency, 3),
            status=status,
            is_simulated=True
        )
