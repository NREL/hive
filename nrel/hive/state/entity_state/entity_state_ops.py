from __future__ import annotations

from typing import Tuple, Optional, TYPE_CHECKING

from nrel.hive.util.exception import StateTransitionError

if TYPE_CHECKING:
    from nrel.hive.state.simulation_state.simulation_state import SimulationState
    from nrel.hive.state.vehicle_state.vehicle_state import VehicleState
    from nrel.hive.runner.environment import Environment


def transition_previous_to_next(
    sim: SimulationState,
    env: Environment,
    prev_state: VehicleState,
    next_state: VehicleState,
) -> Tuple[Optional[Exception], Optional[SimulationState]]:
    """
    exits the previous state and enters the next state

    :param sim: the sim state
    :param env: the sim environment
    :param prev_state: the previous vehicle state
    :param next_state: the next state
    :return: error, or updated sim, or (None, None) if either exit or enter was invalid
    """
    exit_error, exit_sim = prev_state.exit(next_state, sim, env)
    if exit_error:
        prev_state_name = prev_state.__class__.__name__
        next_state_name = next_state.__class__.__name__
        error = StateTransitionError(repr(exit_error), prev_state_name, next_state_name)
        return error, None
    elif not exit_sim:
        return None, None
    else:
        enter_error, enter_sim = next_state.enter(exit_sim, env)
        if enter_error:
            prev_state_name = prev_state.__class__.__name__
            next_state_name = next_state.__class__.__name__
            error = StateTransitionError(repr(enter_error), prev_state_name, next_state_name)
            return error, None
        elif not enter_sim:
            return None, None
        else:
            return None, enter_sim
