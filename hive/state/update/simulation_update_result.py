from typing import NamedTuple, Tuple

from hive.state.simulation_state import SimulationState


class SimulationUpdateResult(NamedTuple):
    simulation_state: SimulationState
    reports: Tuple[str, ...] = ()

