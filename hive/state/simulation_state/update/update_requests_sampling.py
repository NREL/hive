from __future__ import annotations

import functools as ft
import logging
from csv import DictReader
from pathlib import Path
from typing import NamedTuple, Tuple, Optional

from returns.result import Failure

from hive.model.request import RequestRateStructure, Request
from hive.reporting.report_type import ReportType
from hive.reporting.reporter import Report
from hive.runner.environment import Environment
from hive.state.simulation_state.simulation_state import SimulationState
from hive.state.simulation_state import simulation_state_ops
from hive.state.simulation_state.update.simulation_update import (
    SimulationUpdateFunction,
)
from hive.util.iterators import NamedTupleIterator

log = logging.getLogger(__name__)


class UpdateRequestsSampling(NamedTuple, SimulationUpdateFunction):
    """
    injects requests into the simulation based on set of pre-sampled requests.
    """

    request_iterator: NamedTupleIterator
    rate_structure: RequestRateStructure

    @classmethod
    def build(
        cls,
        sampled_requests: Tuple[Request, ...],
        rate_structure_file: Optional[str] = None,
    ):
        """
        reads an optional rate_structure_file and builds a UpdateRequestsFromFile SimulationUpdateFunction


        :param sampled_requests: the pre sampled requests
        :param rate_structure_file: an optional file for a request rate structure

        :return: a SimulationUpdate function that injects the pre-sampled requests based on sim-time
        :raises: an exception if there were issues loading the file
        """
        if rate_structure_file:
            rate_structure_path = Path(rate_structure_file)
            if not rate_structure_path.is_file():
                raise IOError(
                    f"{rate_structure_file} is not a valid path to a request file"
                )
            with open(rate_structure_file, "r", encoding="utf-8-sig") as rsf:
                reader = DictReader(rsf)
                rate_structure = RequestRateStructure.from_row(next(reader))
        else:
            rate_structure = RequestRateStructure()

        stepper = NamedTupleIterator(
            items=sampled_requests,
            step_attr_name="departure_time",
            stop_condition=lambda dt: dt < 0,
        )

        return UpdateRequestsSampling(stepper, rate_structure)

    def update(
        self, sim_state: SimulationState, env: Environment
    ) -> Tuple[SimulationState, Optional[UpdateRequestsSampling]]:
        """
        add requests based on a sampling function


        :param env: the static environment variables
        :param sim_state: the current sim state
        :return: sim state plus new requests
        """

        current_sim_time = sim_state.sim_time

        def stop_condition(value: int) -> bool:
            stop = value < current_sim_time
            return stop

        self.request_iterator.update_stop_condition(stop_condition)

        priced_requests = tuple(
            r.assign_value(self.rate_structure, sim_state.road_network)
            for r in self.request_iterator
        )

        def _add_request(sim: SimulationState, request: Request) -> SimulationState:
            # add request and handle any errors

            new_sim_or_error = simulation_state_ops.add_request_safe(sim, request)
            if isinstance(new_sim_or_error, Failure):
                error = new_sim_or_error.failure()
                log.error(error)
                return sim
            else:
                new_sim = new_sim_or_error.unwrap()
                report_data = {
                    "request_id": request.id,
                    "departure_time": request.departure_time,
                    "fleet_id": str(request.membership),
                }
                env.reporter.file_report(
                    Report(ReportType.ADD_REQUEST_EVENT, report_data)
                )
            return new_sim

        updated_sim = ft.reduce(_add_request, priced_requests, sim_state)

        return updated_sim, self
