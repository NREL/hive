from __future__ import annotations

from pathlib import Path
from typing import NamedTuple, Tuple, Optional, Iterator, Dict
from csv import DictReader
import functools as ft

from hive.model.request import Request, RequestRateStructure
from hive.runner.environment import Environment
from hive.state.simulation_state import SimulationState
from hive.state.update.simulation_update import SimulationUpdateFunction
from hive.state.update.simulation_update_result import SimulationUpdateResult
from hive.util.dict_reader_stepper import DictReaderStepper
from hive.util.parsers import time_parser
from hive.util.typealiases import RequestId


class UpdateRequests(NamedTuple, SimulationUpdateFunction):
    """
    loads requests from a file, which is assumed to be sorted by Request
    """
    reader: DictReaderStepper
    rate_structure: RequestRateStructure

    @classmethod
    def build(cls, request_file: str, rate_structure_file: str):
        """
        reads a requests file and builds a UpdateRequestsFromFile SimulationUpdateFunction

        :param request_file: file path for requests
        :return: a SimulationUpdate function pointing at the first line of a request file
        """
        req_path = Path(request_file)
        rate_structure_path = Path(rate_structure_file)
        if not req_path.is_file():
            raise IOError(f"{request_file} is not a valid path to a request file")
        elif not rate_structure_path.is_file():
            raise IOError(f"{rate_structure_file} is not a valid path to a request file")
        else:
            stepper = DictReaderStepper.from_file(request_file, "departure_time", parser=time_parser)

            with open(rate_structure_file, 'r', encoding='utf-8-sig') as rsf:
                reader = DictReader(rsf)
                rate_structure = RequestRateStructure.from_row(next(reader))

            return UpdateRequests(stepper, rate_structure)

    def update(self,
               sim_state: SimulationState,
               env: Environment) -> Tuple[SimulationUpdateResult, Optional[UpdateRequests]]:
        """
        add requests from file when the simulation reaches the request's time

        :param env: the static environment variables
        :param sim_state: the current sim state
        :return: sim state plus new requests
        """

        current_sim_time = sim_state.sim_time

        def stop_condition(value: int) -> bool:
            return value < current_sim_time

        result = update_requests_from_iterator(
            self.reader.read_until_stop_condition(stop_condition),
            sim_state,
            env=env,
            rate_structure=self.rate_structure,
        )

        return result, None


def update_requests_from_iterator(it: Iterator[Dict[str, str]],
                                  initial_sim_state: SimulationState,
                                  env: Environment,
                                  rate_structure: RequestRateStructure,
                                  ) -> SimulationUpdateResult:
    """
    add requests from file when the simulation reaches the request's time

    :param it: expected to be a Request iterator which streams in row data taken from a DictReader
    :param initial_sim_state: the current sim state
    :param rate_structure:
    :param env:
    :return: sim state plus new requests
    """

    def _update(acc: SimulationUpdateResult, row: Dict[str, str],
                env: Environment,
                rate_structure: RequestRateStructure,
                ) -> SimulationUpdateResult:
        """
        takes one row, attempts to parse it as a Request, and attempts to add it to the simulation

        :param acc: latest SimulationState and any update reports
        :param row: one row as loaded via DictReader
        :return: the updated sim and updated reporting
        """
        req = Request.from_row(row, env)
        if isinstance(req, IOError):
            # request failed to parse from row
            row_failure = _failure_as_json(str(req), acc.simulation_state)
            # TODO: Add to error logger
            print(f"[warning] {req}")
            return acc.add_report(row_failure)
        elif req.cancel_time <= acc.simulation_state.sim_time:
            # cannot add request that should already be cancelled
            current_time = acc.simulation_state.sim_time
            msg = f"request {req.id} with cancel_time {req.cancel_time} cannot be added at time {current_time}"
            invalid_cancel_time = _failure_as_json(msg, acc.simulation_state)
            # TODO: Add to error logger
            print(invalid_cancel_time)
            return acc.add_report(invalid_cancel_time)
        else:
            sim_updated = acc.simulation_state.add_request(req.assign_value(rate_structure))
            if isinstance(sim_updated, Exception):
                # simulation failed to add this request
                sim_failure = _failure_as_json(str(sim_updated), acc.simulation_state)
                # TODO: Add to error logger
                print(f"[warning] {sim_updated}")
                return acc.add_report(sim_failure)
            else:
                # successfully added request
                sim_success = _success_as_json(req.id, sim_updated)
                return acc.update_sim(sim_updated, sim_success)

    # stream in all Requests that occur before the sim time of the provided SimulationState
    updated_sim = ft.reduce(
        ft.partial(_update, env=env, rate_structure=rate_structure),
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
    return f"{{\"report\":\"add_request\",\"sim_time\":\"{sim.sim_time}\",\"error\":\"{error_msg}\"}}"


def _eof_as_json(sim: SimulationState) -> str:
    """
    notification of end-of-file

    :param sim: the simulation state
    :return: a stringified end-of-file report
    """
    return f"{{\"report\":\"add_request\",\"sim_time\":\"{sim.sim_time}\",\"message\":\"EOF\"}}"
