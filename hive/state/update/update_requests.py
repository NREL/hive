from __future__ import annotations

from pathlib import Path
from typing import NamedTuple, Tuple, Optional, Iterator, Dict
from csv import DictReader
import functools as ft
import logging

from hive.model.request import Request, RequestRateStructure
from hive.runner.environment import Environment
from hive.state.simulation_state import SimulationState
from hive.state.update.simulation_update import SimulationUpdateFunction
from hive.state.update.simulation_update_result import SimulationUpdateResult
from hive.util.dict_reader_stepper import DictReaderStepper
from hive.util.parsers import time_parser
from hive.util.typealiases import RequestId

log = logging.getLogger(__name__)


class UpdateRequests(NamedTuple, SimulationUpdateFunction):
    """
    loads requests from a file, which is assumed to be sorted by Request
    """
    reader: DictReaderStepper
    rate_structure: RequestRateStructure

    @classmethod
    def build(cls, request_file: str, rate_structure_file: Optional[str] = None):
        """
        reads a requests file and builds a UpdateRequestsFromFile SimulationUpdateFunction

        :param request_file: file path for requests
        :param rate_structure_file:
        :return: a SimulationUpdate function pointing at the first line of a request file
        """
        rate_structure = RequestRateStructure()
        if rate_structure_file:
            rate_structure_path = Path(rate_structure_file)
            if not rate_structure_path.is_file():
                raise IOError(f"{rate_structure_file} is not a valid path to a request file")
            with open(rate_structure_file, 'r', encoding='utf-8-sig') as rsf:
                reader = DictReader(rsf)
                rate_structure = RequestRateStructure.from_row(next(reader))

        req_path = Path(request_file)
        if not req_path.is_file():
            raise IOError(f"{request_file} is not a valid path to a request file")

        stepper = DictReaderStepper.from_file(request_file, "departure_time", parser=time_parser)

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
        try:
            req = Request.from_row(row, env, acc.simulation_state.road_network)
        except IOError:
            log.exception("failed to parse request from row")
            return acc

        if req.cancel_time <= acc.simulation_state.sim_time:
            # cannot add request that should already be cancelled
            current_time = acc.simulation_state.sim_time
            msg = f"request {req.id} with cancel_time {req.cancel_time} cannot be added at time {current_time}"
            log.warning(msg)
            return acc
        else:
            distance_km = acc.simulation_state.road_network.distance_by_geoid_km(req.origin, req.destination)
            sim_updated = acc.simulation_state.add_request(req.assign_value(rate_structure, distance_km))
            if sim_updated:
                # successfully added request
                sim_success = _gen_report(req.id, sim_updated)
                return acc.update_sim(sim_updated, sim_success)

    # stream in all Requests that occur before the sim time of the provided SimulationState
    updated_sim = ft.reduce(
        ft.partial(_update, env=env, rate_structure=rate_structure),
        it,
        SimulationUpdateResult(initial_sim_state)
    )

    return updated_sim


def _gen_report(r_id: RequestId, sim: SimulationState) -> dict:
    """
    stringified json report of a cancellation

    :param r_id: request cancelled
    :param sim: the state of the sim before cancellation occurs
    :return: a stringified json report
    """
    dep_t = sim.requests[r_id].departure_time
    report = {
        'report_type': 'add_request',
        'request_id': r_id,
        'departure_time': dep_t,
    }
    return report


