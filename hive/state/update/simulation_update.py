from __future__ import annotations

from abc import abstractmethod
from typing import Optional, Tuple

from hive.util.abc_named_tuple_meta import ABCNamedTupleMeta
from hive.state.simulation_state import SimulationState
from hive.state.update.simulation_update_result import SimulationUpdateResult


class SimulationUpdateFunction(metaclass=ABCNamedTupleMeta):

    @abstractmethod
    def update(self,
               simulation_state: SimulationState) -> Tuple[SimulationUpdateResult, Optional[SimulationUpdateFunction]]:
        """
        takes a simulation state and modifies it, returning the updated simulation state

        :param simulation_state: the state to modify
        :return: the updated sim state, along with any reporting;
        as well, an Optionally-updated SimulationUpdate function
        """
        pass

