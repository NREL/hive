from abc import abstractmethod
from typing import Tuple, Optional

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


def transition(sim: SimulationState,
               env: Environment,
               prev_state: EntityState,
               next_state: EntityState
               ) -> Tuple[Optional[Exception], Optional[SimulationState]]:
    """
    exits the previous state and enters the next state
    :param sim: the sim state
    :param env: the sim environment
    :param prev_state: the previous vehicle state
    :param next_state: the next state
    :return: error, or updated sim, or sim with no change if enter was invalid
    """
    exit_error, exit_sim = prev_state.exit(sim, env)
    if exit_error:
        return exit_error, None
    else:
        enter_error, enter_sim = next_state.enter(exit_sim, env)
        if enter_error:
            return enter_error, None
        elif not enter_sim:
            return None, sim
        else:
            return None, enter_sim
