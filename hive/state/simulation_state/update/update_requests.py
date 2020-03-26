from __future__ import annotations

from pathlib import Path
from typing import NamedTuple, Tuple, Optional, Iterator, Dict
from csv import DictReader
import functools as ft
import logging

from hive.model.request import Request, RequestRateStructure
from hive.runner.environment import Environment
from hive.state.simulation_state import simulation_state_ops
from hive.state.simulation_state.simulation_state import SimulationState
from hive.state.simulation_state.update.simulation_update import SimulationUpdateFunction
from hive.state.simulation_state.update.simulation_update_result import SimulationUpdateResult
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
        :raises: an exception if there were issues loading the file
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

        error, stepper = DictReaderStepper.from_file(request_file, "departure_time", parser=time_parser)
        if error:
            raise error
        else:
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

    def _update(acc: SimulationUpdateResult,
                row: Dict[str, str],
                env: Environment,
                rate_structure: RequestRateStructure,
                ) -> SimulationUpdateResult:
        """
        takes one row, attempts to parse it as a Request, and attempts to add it to the simulation

        :param acc: latest SimulationState and any update reports
        :param row: one row as loaded via DictReader
        :param env: the simulation environment
        :param rate_structure: the rate structure for requests in the simulation
        :return: the updated sim and updated reporting
        """
        error, req = Request.from_row(row, env, acc.simulation_state.road_network)
        if error:
            return acc.add_report({'error': error})
        elif req.cancel_time <= acc.simulation_state.sim_time:
            # cannot add request that should already be cancelled
            current_time = acc.simulation_state.sim_time
            warning = f"request {req.id} with cancel_time {req.cancel_time} cannot be added at time {current_time}"
            return acc.add_report({'warning': warning})
        else:
            distance_km = acc.simulation_state.road_network.distance_by_geoid_km(req.origin, req.destination)
            req_updated = req.assign_value(rate_structure, distance_km)
            error, sim_updated = simulation_state_ops.add_request(acc.simulation_state, req_updated)
            if error:
                return acc.add_report({'error': error})
            else:
                # successfully added request
                req_in_sim = sim_updated.requests.get(req.id)
                if not req_in_sim:
                    warning = f"adding new request {req.id} to sim succeeded but now request is not found"
                    return acc.add_report({'warning': warning})
                else:
                    dep_t = sim_updated.requests.get(req.id).departure_time
                    report = {
                        'report_type': 'add_request',
                        'request_id': req.id,
                        'departure_time': dep_t,
                    }
                    return acc.update_sim(sim_updated, report)

    # stream in all Requests that occur before the sim time of the provided SimulationState
    updated_sim = ft.reduce(
        ft.partial(_update, env=env, rate_structure=rate_structure),
        it,
        SimulationUpdateResult(initial_sim_state)
    )

    return updated_sim

