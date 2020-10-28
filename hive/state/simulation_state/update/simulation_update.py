from __future__ import annotations

from abc import abstractmethod
from typing import Optional, Tuple, TYPE_CHECKING

from hive.util.abc_named_tuple_meta import ABCNamedTupleMeta

if TYPE_CHECKING:
    from hive.state.simulation_state.simulation_state import SimulationState
    from hive.runner.environment import Environment


class SimulationUpdateFunction(metaclass=ABCNamedTupleMeta):

    @abstractmethod
    def update(self,
               simulation_state: SimulationState,
               env: Environment) -> Tuple[SimulationState, Optional[SimulationUpdateFunction]]:
        """
        takes a simulation state and modifies it, returning the updated simulation state


        :param simulation_state: the state to modify
        :param env: the environmental variables for this run
        :return: the updated sim state, along with any reporting;
        as well, an Optionally-updated SimulationUpdate function
        """

