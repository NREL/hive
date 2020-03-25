from __future__ import annotations

import functools as ft
from typing import Tuple, Optional, NamedTuple, Dict

from hive.runner.environment import Environment
from hive.state.simulation_state.simulation_state import SimulationState
from hive.state.simulation_state.update.simulation_update import SimulationUpdateFunction
from hive.state.simulation_state.update.simulation_update_result import SimulationUpdateResult
from hive.util.exception import report_error
from hive.util.typealiases import RequestId


class CancelRequests(NamedTuple, SimulationUpdateFunction):

    def update(
            self,
            simulation_state: SimulationState,
            env: Environment) -> Tuple[SimulationUpdateResult, Optional[CancelRequests]]:
        """
        cancels requests whose cancel time has been exceeded

        :param simulation_state: state to modify
        :param env: the scenario environment
        :return: state without cancelled requests, along with this update function
        """

        def _remove_from_sim(payload: Tuple[SimulationState, Tuple[Dict, ...]],
                             request_id: RequestId) -> Tuple[SimulationState, Tuple[Dict, ...]]:
            """
            inner function that removes each canceled request from the sim
            :param payload: the sim to update, along with errors we are storing
            :param request_id: this request to remove
            :return: the sim without the request
            """
            sim, these_reports = payload
            this_request_cancel_time = sim.requests[request_id].cancel_time
            if sim.sim_time < this_request_cancel_time:
                return payload
            else:
                # remove this request
                update_error, updated_sim = sim.remove_request(request_id)

                # report either error or successful cancellation
                if update_error:
                    report = report_error(update_error)
                    updated_reports = these_reports + (report,)
                    return sim, updated_reports
                else:
                    report = _gen_report(request_id, sim)  # use the pre-updated sim so we can lookup this request
                    updated_reports = these_reports + (report,)
                    return updated_sim, updated_reports

        updated, reports = ft.reduce(
            _remove_from_sim,
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
