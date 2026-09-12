"""Simulation orchestration and deterministic timestep execution."""

from datetime import datetime, timedelta

from backend.common.events import Events, event_bus
from backend.common.exceptions import SimulationError
from backend.common.logger import get_module_logger
from backend.common.schemas.enums import ScenarioType
from backend.common.schemas.microgrid_state import MicrogridState
from backend.modules.simulation.dynamics import advance_timestep
from backend.modules.simulation.environment import MicrogridEnvironment
from backend.modules.simulation.schemas import (
    ControlInputs,
    CrisisScenario,
    EnvironmentalConditions,
    SimulationConfig,
    SimulationStepResult,
    build_scenario,
    primary_crisis_scenario,
)
from backend.modules.simulation.state import MicrogridStateManager


log = get_module_logger("simulation.service")


class SimulationService:
    """A deterministic physical world for the GridMind agents to observe.

    The engine never selects actions.  It accepts optional, already-resolved
    ``ControlInputs`` and applies them subject to physical constraints.  The
    critical facility has fixed allocation priority whenever supply is scarce.
    """

    def __init__(self, config: SimulationConfig | None = None):
        self.config = config or SimulationConfig()
        self.environment = MicrogridEnvironment(self.config)
        self.state_manager = MicrogridStateManager()
        self.active_scenario: CrisisScenario | None = None
        self.last_result: SimulationStepResult | None = None
        self._started_at: datetime | None = None
        self._scenario_was_active = False

    @property
    def is_initialized(self) -> bool:
        return self.last_result is not None

    def initialize(
        self,
        *,
        conditions: EnvironmentalConditions | None = None,
        start_time: datetime | None = None,
    ) -> MicrogridState:
        """Create the baseline timestep-zero shared state."""
        self.environment = MicrogridEnvironment(self.config)
        self.state_manager.clear()
        self.last_result = None
        self._scenario_was_active = False
        self._started_at = start_time or self.config.simulation_start_time
        result = self._advance(
            timestep=0,
            controls=ControlInputs(),
            environmental_conditions=conditions,
            timestamp=self._started_at,
        )
        event_bus.publish(Events.MICROGRID_INITIALIZED, result.state)
        log.info("Simulation initialized")
        return result.state.model_copy(deep=True)

    def get_state(self) -> MicrogridState:
        """Return the current shared-state snapshot."""
        return self.state_manager.get_current()

    def get_history(self) -> list[MicrogridState]:
        """Return copies of every state produced in this run."""
        return self.state_manager.get_history()

    def get_last_result(self) -> SimulationStepResult:
        """Return detailed accounting for the most recently completed step."""
        if self.last_result is None:
            raise SimulationError("Simulation has not been initialized")
        return self.last_result.model_copy(deep=True)

    def apply_scenario(self, scenario: CrisisScenario) -> None:
        """Register one exogenous crisis scenario for future timesteps."""
        self.active_scenario = scenario
        event_bus.publish(
            Events.SCENARIO_TRIGGERED,
            {
                "scenario": scenario.scenario_type.value,
                "start_timestep": scenario.start_timestep,
                "duration_steps": scenario.duration_steps,
            },
        )

    def apply_primary_crisis(
        self,
        *,
        start_timestep: int | None = None,
        duration_steps: int | None = None,
    ) -> CrisisScenario:
        """Schedule solar −50% and flexible-demand +30% for the next step."""
        if start_timestep is None:
            start_timestep = (self.get_state().timestep + 1) if self.is_initialized else 1
        scenario = primary_crisis_scenario(
            start_timestep=start_timestep,
            duration_steps=duration_steps,
        )
        self.apply_scenario(scenario)
        return scenario

    def step(
        self,
        controls: ControlInputs | None = None,
        *,
        conditions: EnvironmentalConditions | None = None,
    ) -> MicrogridState:
        """Execute exactly one deterministic physical timestep."""
        if not self.is_initialized:
            self.initialize()
        current = self.get_state()
        timestep = current.timestep + 1
        timestamp = current.timestamp + timedelta(seconds=self.config.timestep_seconds)
        try:
            result = self._advance(
                timestep=timestep,
                controls=controls or ControlInputs(),
                environmental_conditions=conditions,
                timestamp=timestamp,
            )
        except Exception as error:
            event_bus.publish(
                Events.SIMULATION_ERROR,
                {"timestep": timestep, "error": str(error)},
            )
            if isinstance(error, SimulationError):
                raise
            raise SimulationError(str(error), step=timestep) from error

        event_bus.publish(Events.SIMULATION_STEP_COMPLETED, result.state)
        event_bus.publish(Events.MICROGRID_STATE_CHANGED, result.state)
        self._publish_scenario_completion_if_needed(timestep)
        return result.state.model_copy(deep=True)

    def run(self) -> list[MicrogridState]:
        """Run GridMind's defined 13-step simulation loop.

        ``loop.py`` owns the loop cadence so the service remains responsible
        only for orchestration and individual physical transitions.
        """
        from backend.modules.simulation.loop import SimulationLoop

        return SimulationLoop(self).run()

    def reset(self) -> None:
        """Discard the current in-memory run and its state history."""
        self.environment = MicrogridEnvironment(self.config)
        self.state_manager.clear()
        self.active_scenario = None
        self.last_result = None
        self._started_at = None
        self._scenario_was_active = False

    def _advance(
        self,
        *,
        timestep: int,
        controls: ControlInputs,
        environmental_conditions: EnvironmentalConditions | None,
        timestamp: datetime,
    ) -> SimulationStepResult:
        conditions, solar_multiplier, flexible_multiplier = self.environment.resolve_conditions(
            environmental_conditions,
            self.active_scenario,
            timestep,
        )
        result = advance_timestep(
            environment=self.environment,
            config=self.config,
            timestep=timestep,
            timestamp=timestamp,
            controls=controls,
            conditions=conditions,
            solar_generation_multiplier=solar_multiplier,
            flexible_demand_multiplier=flexible_multiplier,
            active_scenario=self.active_scenario,
        )
        stored_state = self.state_manager.set_state(result.state)
        self.last_result = result.model_copy(update={"state": stored_state})
        return self.last_result

    def _publish_scenario_completion_if_needed(self, timestep: int) -> None:
        is_active = bool(self.active_scenario and self.active_scenario.is_active_at(timestep))
        if self._scenario_was_active and not is_active and self.active_scenario is not None:
            event_bus.publish(
                Events.SCENARIO_COMPLETED,
                {"scenario": self.active_scenario.scenario_type.value, "timestep": timestep},
            )
        self._scenario_was_active = is_active

    def set_scenario_type(
        self,
        scenario_type: ScenarioType,
        *,
        start_timestep: int | None = None,
        duration_steps: int | None = None,
    ) -> CrisisScenario:
        """Convenience wrapper that accepts only supported common enum values."""
        if start_timestep is None:
            start_timestep = (self.get_state().timestep + 1) if self.is_initialized else 1
        scenario = build_scenario(
            scenario_type,
            start_timestep=start_timestep,
            duration_steps=duration_steps,
        )
        self.apply_scenario(scenario)
        return scenario


# A descriptive compatibility alias for callers that refer to the component as
# the "simulation engine" rather than its architectural service role.
SimulationEngine = SimulationService
