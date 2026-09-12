"""The fixed 13-step GridMind simulation loop."""

from typing import TYPE_CHECKING

from backend.common.events import Events, event_bus
from backend.common.schemas.microgrid_state import MicrogridState

if TYPE_CHECKING:
    from backend.modules.simulation.service import SimulationService


SIMULATION_LOOP_STEPS = 13


class SimulationLoop:
    """Runs exactly thirteen physical transitions without calling agents."""

    def __init__(self, service: "SimulationService") -> None:
        self.service = service

    def run(self) -> list[MicrogridState]:
        """Initialize if needed, publish lifecycle events, and run 13 steps."""
        if not self.service.is_initialized:
            self.service.initialize()
        event_bus.publish(
            Events.SIMULATION_STARTED,
            {"simulation_run_id": self.service.config.simulation_run_id, "steps": SIMULATION_LOOP_STEPS},
        )
        states: list[MicrogridState] = []
        try:
            for _ in range(SIMULATION_LOOP_STEPS):
                states.append(self.service.step())
        except Exception as error:
            event_bus.publish(
                Events.SIMULATION_ERROR,
                {"timestep": self.service.get_state().timestep, "error": str(error)},
            )
            raise
        event_bus.publish(
            Events.SIMULATION_FINISHED,
            {"simulation_run_id": self.service.config.simulation_run_id, "steps": SIMULATION_LOOP_STEPS},
        )
        return states
