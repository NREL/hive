from __future__ import annotations

import functools as ft
from typing import Tuple, Optional, NamedTuple

from hive.runner.environment import Environment
from hive.state.simulation_state import SimulationState
from hive.state.update.simulation_update import SimulationUpdateFunction
from hive.state.update.simulation_update_result import SimulationUpdateResult
from hive.util.typealiases import RequestId


class CancelRequests(NamedTuple, SimulationUpdateFunction):

    def update(
            self,
            simulation_state: SimulationState,
            env: Environment) -> Tuple[SimulationUpdateResult, Optional[CancelRequests]]:
        """
        cancels requests whose cancel time has been exceeded

        :param simulation_state: state to modify
        :return: state without cancelled requests, along with this update function
        """

        # TODO: think about making this more readable and catching if simulation_state.remove_request fails
        updated, reports = ft.reduce(
            lambda s, r_id: (s[0].remove_request(r_id), s[1] + (_gen_report(r_id, s[0]),)) \
                if s[0].sim_time >= s[0].requests[r_id].cancel_time \
                else s,
            simulation_state.requests.keys(),
            (simulation_state, ())
        )

        return SimulationUpdateResult(updated, reports), None


def _gen_report(r_id: RequestId, sim: SimulationState) -> dict:
    """
    stringified json report of a cancellation

    :param r_id: request cancelled
    :param sim: the state of the sim before cancellation occurs
    :return: a stringified json report
    """
    dep_t = sim.requests[r_id].departure_time
    sim_t = sim.sim_time
    report = {
        'report_type': 'cancel_request',
        'request_id': r_id,
        'departure_time': dep_t,
        'cancel_time': sim_t,
    }
    return report
