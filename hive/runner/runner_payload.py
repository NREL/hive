from __future__ import annotations

from typing import NamedTuple, TYPE_CHECKING


if TYPE_CHECKING:
    from hive.state.simulation_state.update.update import Update
    from hive.runner.environment import Environment
    from hive.state.simulation_state.simulation_state import SimulationState


class RunnerPayload(NamedTuple):
    """
    Holds the simulation state, dispatcher and reports for the simulation run.


    :param s: the simulation state
    :type s: :py:obj:`SimulationState`

    :param e: the environmental assets for this simulation
    :type e: :py:obj:`Environment`

    :param u: the updates we need to apply during each sim step
    :type u: :py:obj:`Update`
    """
    s: SimulationState
    e: Environment
    u: Update
