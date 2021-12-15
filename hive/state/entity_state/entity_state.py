from __future__ import annotations
from abc import abstractmethod
from typing import Tuple, Optional


# if TYPE_CHECKING:
#     from hive.state.simulation_state import SimulationState
#     from hive.runner.environment import Environment


class EntityState:
    """
    a state representation along with methods for state transitions and discrete time step updates
    """

    @abstractmethod
    def update(self,
               sim: 'SimulationState',
               env: 'Environment',
               ) -> Tuple[Optional[Exception], Optional['SimulationState']]:
        """
        apply any effects due to an entity being advanced one discrete time unit in this EntityState

        :param sim: the simulation state
        :param env: the simulation environment
        :return: an exception due to failure or an optional updated simulation
        """
        pass

    @abstractmethod
    def enter(self,
              sim: 'SimulationState',
              env: 'Environment') -> Tuple[Optional[Exception], Optional['SimulationState']]:
        """
        apply any effects due to an entity transitioning into this state

        :param sim: the simulation state
        :param env: the simulation environment
        :return: an exception due to failure or an optional updated simulation, or (None, None) if invalid
        """
        pass

    @abstractmethod
    def exit(self,
             next_state: EntityState,
             sim: 'SimulationState',
             env: 'Environment') -> Tuple[Optional[Exception], Optional['SimulationState']]:
        """
        apply any effects due to an entity transitioning out of this state

        :param next_state the EntityState to transition to
        :param sim: the simulation state
        :param env: the simulation environment
        :return: an exception due to failure or an optional updated simulation, or (None, None) if invalid
        """
        pass
