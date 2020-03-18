from abc import abstractmethod
from typing import Tuple, Optional

from hive.util.abc_named_tuple_meta import ABCNamedTupleMeta

from hive.runner.environment import Environment
from hive.state.simulation_state import SimulationState


class EntityState:
    """
    a state representation along with methods for state transitions and discrete time step updates
    """

    @abstractmethod
    def update(self,
               sim: SimulationState,
               env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        """
        apply any effects due to an entity being advanced one discrete time unit in this EntityState
        :param sim: the simulation state
        :param env: the simulation environment
        :return: an exception due to failure or an optional updated simulation
        """
        pass

    @abstractmethod
    def enter(self,
              sim: SimulationState,
              env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        """
        apply any effects due to an entity transitioning into this state
        :param sim: the simulation state
        :param env: the simulation environment
        :return: an exception due to failure or an optional updated simulation
        """
        pass

    @abstractmethod
    def exit(self,
             sim: SimulationState,
             env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        """
        apply any effects due to an entity transitioning out of this state
        :param sim: the simulation state
        :param env: the simulation environment
        :return: an exception due to failure or an optional updated simulation
        """
        pass
