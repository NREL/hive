from typing import Dict, Iterator

import functools as ft

from hive.model.request import Request
from hive.state.simulation_state import SimulationState
from hive.state.update.simulation_update_result import SimulationUpdateResult
from hive.util.typealiases import RequestId


def update_requests_from_iterator(it: Iterator[Dict[str, str]],
                                  initial_sim_state: SimulationState) -> SimulationUpdateResult:
    """
    add requests from file when the simulation reaches the request's time

    :param it: expected to be a Request iterator which streams in row data taken from a DictReader
    :param initial_sim_state: the current sim state
    :return: sim state plus new requests
    """

    def _update(acc: SimulationUpdateResult, row: Dict[str, str]) -> SimulationUpdateResult:
        """
        takes one row, attempts to parse it as a Request, and attempts to add it to the simulation

        :param acc: latest SimulationState and any update reports
        :param row: one row as loaded via DictReader
        :return: the updated sim and updated reporting
        """
        req = Request.from_row(row, acc.simulation_state.road_network)
        if isinstance(req, IOError):
            # request failed to parse from row
            row_failure = _failure_as_json(str(req), acc.simulation_state)
            return acc.add_report(row_failure)
        elif req.cancel_time <= acc.simulation_state.current_time:
            # cannot add request that should already be cancelled
            current_time = acc.simulation_state.current_time
            msg = f"request {req.id} with cancel_time {req.cancel_time} cannot be added at time {current_time}"
            invalid_cancel_time = _failure_as_json(msg, acc.simulation_state)
            return acc.add_report(invalid_cancel_time)
        else:
            sim_updated = acc.simulation_state.add_request(req)
            if isinstance(sim_updated, Exception):
                # simulation failed to add this request
                sim_failure = _failure_as_json(str(sim_updated), acc.simulation_state)
                return acc.add_report(sim_failure)
            else:
                # successfully added request
                sim_success = _success_as_json(req.id, sim_updated)
                return acc.update_sim(sim_updated, sim_success)

    # stream in all Requests that occur before the sim time of the provided SimulationState
    updated_sim = ft.reduce(
        _update,
        it,
        SimulationUpdateResult(initial_sim_state)
    )

    return updated_sim


def _success_as_json(r_id: RequestId, sim: SimulationState) -> str:
    """
    stringified json report of a cancellation

    :param r_id: request cancelled
    :param sim: the state of the sim before cancellation occurs
    :return: a stringified json report
    """
    dep_t = sim.requests[r_id].departure_time
    return f"{{\"report\":\"add_request\",\"request_id\":\"{r_id}\",\"departure_time\":\"{dep_t}\"}}"


def _failure_as_json(error_msg: str, sim: SimulationState) -> str:
    """
    stringified json report of a cancellation

    :param error_msg: error message
    :param sim: the state of the sim before cancellation occurs
    :return: a stringified json report of an error
    """
    return f"{{\"report\":\"add_request\",\"sim_time\":\"{sim.current_time}\",\"error\":\"{error_msg}\"}}"


def _eof_as_json(sim: SimulationState) -> str:
    """
    notification of end-of-file

    :param sim: the simulation state
    :return: a stringified end-of-file report
    """
    return f"{{\"report\":\"add_request\",\"sim_time\":\"{sim.current_time}\",\"message\":\"EOF\"}}"
