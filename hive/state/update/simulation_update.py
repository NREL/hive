from __future__ import annotations

from abc import ABC, abstractmethod, ABCMeta

from hive.state.simulation_state import SimulationState
from hive.state.update.simulation_update_result import SimulationUpdateResult


class SimulationUpdate(ABC):

    @abstractmethod
    def update(self, simulation_state: SimulationState) -> SimulationUpdateResult:
        """
        takes a simulation state and modifies it, returning the updated simulation state
        :param simulation_state: the state to modify
        :return: the updated sim state, along with any reporting
        """
        pass
