from typing import Tuple, Optional

from hive.state.entity_state.entity_state import EntityState
from hive.runner.environment import Environment


def transition_previous_to_next(sim: 'SimulationState',
                                env: Environment,
                                prev_state: EntityState,
                                next_state: EntityState
                                ) -> Tuple[Optional[Exception], Optional['SimulationState']]:
    """
    exits the previous state and enters the next state
    :param sim: the sim state
    :param env: the sim environment
    :param prev_state: the previous vehicle state
    :param next_state: the next state
    :return: error, or updated sim, or (None, None) if enter was invalid
    """
    exit_error, exit_sim = prev_state.exit(sim, env)
    if exit_error:
        return exit_error, None
    else:
        enter_error, enter_sim = next_state.enter(exit_sim, env)
        if enter_error:
            return enter_error, None
        elif not enter_sim:
            return None, None
        else:
            return None, enter_sim
