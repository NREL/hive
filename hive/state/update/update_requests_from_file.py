from __future__ import annotations

import csv
from pathlib import Path

from hive.model.request import Request
from hive.state.simulation_state import SimulationState, RequestId
from hive.state.update.simulation_update import SimulationUpdate
from hive.state.update.simulation_update_result import SimulationUpdateResult


class UpdateRequestsFromFile(SimulationUpdate):
    """
    loads requests from a file, which is assumed to be sorted by Request
    """

    def __init__(self, request_file: str):
        """
        reads a requests file and builds a UpdateRequestsFromFile SimulationUpdate function
        :param request_file: file path for requests
        :return: a SimulationUpdate function pointing at the first line of a request file
        """
        req_path = Path(request_file)
        if not req_path.is_file():
            raise IOError(f"{request_file} is not a valid path to a request file")
        else:
            self.requests = csv.DictReader(open(req_path, newline=''))
            self.pointer = 0

    def update(self, simulation_state: SimulationState) -> SimulationUpdateResult:
        """
        add requests from file when the simulation reaches the request's time
        :param simulation_state: the current sim state
        :return: sim state plus new requests
        """

        try:
            row = next(self.requests)
            req = Request.from_row(row, simulation_state.road_network)
            if isinstance(req, IOError):
                report = _failure_as_json(str(req), simulation_state)
                return SimulationUpdateResult(simulation_state, (report, ))
            else:
                sim_updated = simulation_state.add_request(req)
                if isinstance(sim_updated, Exception):
                    report = _failure_as_json(str(sim_updated), simulation_state)
                    return SimulationUpdateResult(simulation_state, (report,))
                else:
                    return SimulationUpdateResult(sim_updated)
        except StopIteration:
            report = _eof_as_json(simulation_state)
            return SimulationUpdateResult(simulation_state, (report, ))


def _success_as_json(r_id: RequestId, sim: SimulationState) -> str:
    """
    stringified json report of a cancellation
    :param r_id: request cancelled
    :param sim: the state of the sim before cancellation occurs
    :return: a stringified json report
    """
    dep_t = sim.requests[r_id].departure_time
    return f"{{'report':'add_request','request_id':'{r_id}','departure_time':'{dep_t}}}"


def _failure_as_json(error_msg: str, sim: SimulationState) -> str:
    """
    stringified json report of a cancellation
    :param error_msg: error message
    :param sim: the state of the sim before cancellation occurs
    :return: a stringified json report of an error
    """
    return f"{{'report':'add_request','sim_time':'{sim.sim_time}','error':'{error_msg}'}}"


def _eof_as_json(sim: SimulationState) -> str:
    """
    notification of end-of-file
    :param sim: the simulation state
    :return: a stringified end-of-file report
    """
    return f"{{'report':'add_request','sim_time':'{sim.sim_time}','message':'EOF'}}"
