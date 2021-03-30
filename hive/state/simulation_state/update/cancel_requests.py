from __future__ import annotations

import functools as ft
from typing import Tuple, Optional, NamedTuple

from hive.runner.environment import Environment
from hive.state.simulation_state import simulation_state_ops
from hive.state.simulation_state.simulation_state import SimulationState
from hive.state.simulation_state.update.simulation_update import SimulationUpdateFunction
from hive.util.typealiases import RequestId
from hive.reporting.reporter import Report, ReportType

import logging

log = logging.getLogger(__name__)


class CancelRequests(NamedTuple, SimulationUpdateFunction):

    def update(
            self,
            simulation_state: SimulationState,
            env: Environment) -> Tuple[SimulationState, Optional[CancelRequests]]:
        """
        cancels requests whose cancel time has been exceeded


        :param simulation_state: state to modify
        :param env: the scenario environment
        :return: state without cancelled requests, along with this update function
        """

        def _remove_from_sim(sim: SimulationState,
                             request_id: RequestId) -> SimulationState:
            """
            inner function that removes each canceled request from the sim

            :param payload: the sim to update, along with errors we are storing
            :param request_id: this request to remove
            :return: the sim without the request
            """
            this_request_cancel_time = sim.requests[
                                           request_id].departure_time + env.config.sim.request_cancel_time_seconds
            if sim.sim_time < this_request_cancel_time:
                return sim
            else:
                # remove this request
                update_error, updated_sim = simulation_state_ops.remove_request(sim, request_id)

                # report either error or successful cancellation
                if update_error:
                    log.error(update_error)
                    return sim
                else:
                    env.reporter.file_report(_gen_report(request_id, sim))
                    return updated_sim

        updated = ft.reduce(
            _remove_from_sim,
            simulation_state.requests.keys(),
            simulation_state
        )

        return updated, None


def _gen_report(r_id: RequestId, sim: SimulationState) -> Report:
    """
    Report of a cancellation

    :param r_id: request cancelled
    :param sim: the state of the sim before cancellation occurs
    :return: a report
    """
    dep_t = sim.requests[r_id].departure_time
    sim_t = sim.sim_time
    req = sim.requests.get(r_id)
    membership = str(req.membership) if req else ""
    report_data = {
        'request_id': r_id,
        'departure_time': dep_t,
        'cancel_time': sim_t,
        'fleet_id': membership,
    }
    return Report(ReportType.CANCEL_REQUEST_EVENT, report_data)
