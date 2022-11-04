from __future__ import annotations

from abc import abstractmethod, ABC
from typing import Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from nrel.hive.state.simulation_state.simulation_state import SimulationState
    from nrel.hive.runner.environment import Environment


class SimulationUpdateFunction(ABC):
    @abstractmethod
    def update(
        self, simulation_state: SimulationState, env: Environment
    ) -> Tuple[SimulationState, Optional[SimulationUpdateFunction]]:
        """
        takes a simulation state and modifies it, returning the updated simulation state


        :param simulation_state: the state to modify
        :param env: the environmental variables for this run
        :return: the updated sim state, along with any reporting;
        as well, an Optionally-updated SimulationUpdate function
        """
