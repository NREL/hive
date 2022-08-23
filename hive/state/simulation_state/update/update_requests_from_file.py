from __future__ import annotations

import functools as ft
import logging
from csv import DictReader
from pathlib import Path
from typing import NamedTuple, Tuple, Optional, Iterator, Dict

from returns.result import Failure

from hive.model.request import Request, RequestRateStructure
from hive.model.sim_time import SimTime
from hive.reporting.reporter import Report, ReportType
from hive.runner.environment import Environment
from hive.state.simulation_state import simulation_state_ops
from hive.state.simulation_state.simulation_state import SimulationState
from hive.state.simulation_state.update.simulation_update import SimulationUpdateFunction
from hive.util.iterators import DictReaderStepper

log = logging.getLogger(__name__)


class UpdateRequestsFromFile(NamedTuple, SimulationUpdateFunction):
    """
    loads requests from a file, which is assumed to be sorted by Request
    """
    reader: DictReaderStepper
    rate_structure: RequestRateStructure

    @classmethod
    def build(
            cls,
            request_file: str,
            rate_structure_file: Optional[str] = None,
            lazy_file_reading: bool = False,
    ):
        """
        reads a requests file and builds a UpdateRequestsFromFile SimulationUpdateFunction


        :param request_file: file path for requests
        :param rate_structure_file:
        :param lazy_file_reading: a flag to enable lazy file loading. if false, the update function loads all reqs in memory
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

        if lazy_file_reading:
            error, stepper = DictReaderStepper.build(request_file, "departure_time", parser=SimTime.build)
            if error:
                raise error
        else:
            with req_path.open() as f:
                # converting to tuple then back to iterator should bring the whole file into memory
                reader = iter(tuple(DictReader(f)))

            stepper = DictReaderStepper.from_iterator(reader, "departure_time", parser=SimTime.build)

        return UpdateRequestsFromFile(stepper, rate_structure)

    def update(self,
               sim_state: SimulationState,
               env: Environment) -> Tuple[SimulationState, Optional[UpdateRequestsFromFile]]:
        """
        add requests from file when the simulation reaches the request's time


        :param env: the static environment variables
        :param sim_state: the current sim state
        :return: sim state plus new requests
        """

        current_sim_time = sim_state.sim_time

        def stop_condition(value: int) -> bool:
            stop = value < current_sim_time
            return stop

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
                                  ) -> SimulationState:
    """
    add requests from file when the simulation reaches the request's time


    :param it: expected to be a Request iterator which streams in row data taken from a DictReader
    :param initial_sim_state: the current sim state
    :param rate_structure:
    :param env:
    :return: sim state plus new requests
    """

    def _update(sim: SimulationState,
                row: Dict[str, str],
                env: Environment,
                rate_structure: RequestRateStructure,
                ) -> SimulationState:
        """
        takes one row, attempts to parse it as a Request, and attempts to add it to the simulation


        :param sim: latest SimulationState
        :param row: one row as loaded via DictReader
        :param env: the simulation environment
        :param rate_structure: the rate structure for requests in the simulation
        :return: the updated sim and updated reporting
        """
        error, req = Request.from_row(row, env, sim.road_network)
        this_req_cancel_time = req.departure_time + env.config.sim.request_cancel_time_seconds if req else None
        if error:
            log.error(error)
            return sim
        elif not req:
            log.error(f"an unexpected error occurred with request row: {row}")
            return sim
        elif this_req_cancel_time <= sim.sim_time:
            # cannot add request that should already be cancelled
            current_time = sim.sim_time
            warning = f"request {req.id} with cancel_time {this_req_cancel_time} cannot be added at time {current_time}"
            log.warning(warning)
            return sim
        elif len(env.fleet_ids) > 0 and len(req.membership.memberships) == 0:
            warning = f"request {req.id} is missing membership and will not be be added"
            log.warning(warning)
            return sim
        elif len(env.fleet_ids) == 0 and len(req.membership.memberships) > 0:
            warning = f"request {req.id} has membership but there is no fleets file. This request will not be added"
            log.warning(warning)
            return sim
        else:
            req_updated = req.assign_value(rate_structure, sim.road_network)
            sim_or_error = simulation_state_ops.add_request_safe(sim, req_updated)
            if isinstance(sim, Failure):
                error = sim_or_error.failure()
                log.error(error)
                return sim
            else:
                # successfully added request
                sim_updated = sim_or_error.unwrap()
                req_in_sim = sim_updated.requests.get(req.id)
                if not req_in_sim:
                    warning = f"adding new request {req.id} to sim succeeded but now request is not found"
                    log.warning(warning)
                    return sim
                else:
                    dep_t = sim_updated.requests.get(req.id).departure_time
                    report_data = {
                        'request_id': req.id,
                        'departure_time': dep_t,
                        'fleet_id': str(req.membership)
                    }
                    env.reporter.file_report(Report(ReportType.ADD_REQUEST_EVENT, report_data))
                    return sim_updated

    # stream in all Requests that occur before the sim time of the provided SimulationState
    updated_sim = ft.reduce(
        ft.partial(_update, env=env, rate_structure=rate_structure),
        it,
        initial_sim_state
    )

    return updated_sim
