from __future__ import annotations

import functools as ft
import logging
import random
from csv import DictReader
from pathlib import Path
from typing import NamedTuple, Tuple, Optional, Callable

from hive.model.request import RequestRateStructure, Request
from hive.runner.environment import Environment
from hive.state.simulation_state.simulation_state import SimulationState
from hive.state.simulation_state.simulation_state_ops import add_request
from hive.state.simulation_state.update.simulation_update import SimulationUpdateFunction

log = logging.getLogger(__name__)


def default_request_sampling_function(sim: SimulationState) -> Tuple[Request, ...]:
    """
    a fallback request sampling function that injects N/4 requests at each simulation time step
    where N = number of vehicles in the simulation

    the function uniformly samples random links from the road network


    :param sim: the simulation state

    :return: N_Vehicles / 4 requests
    """
    n_requests = int(len(sim.vehicles) / 4)
    requests = []

    for i in range(n_requests):
        rid = str(sim.sim_time) + "_" + str(i)
        random_origin_link = sim.road_network.random_link()
        random_destination_link = sim.road_network.random_link()

        while random_origin_link.start == random_destination_link.start:
            random_origin_link = sim.road_network.random_link()
            random_destination_link = sim.road_network.random_link()

        request = Request.build(
            request_id=rid,
            origin=random_origin_link.start,
            destination=random_destination_link.start,
            road_network=sim.road_network,
            departure_time=sim.sim_time,
            passengers=random.choice([1, 2, 3, 4]),
        )

        requests.append(request)

    return tuple(requests)


class UpdateRequestsSampling(NamedTuple, SimulationUpdateFunction):
    """
    injects requests into the simulation based on a sampling function.
    """
    sampling_function: Callable[[SimulationState], Tuple[Request]]
    rate_structure: RequestRateStructure

    @classmethod
    def build(
            cls,
            sampling_function: Callable[[SimulationState], Tuple[Request]] = default_request_sampling_function,
            rate_structure_file: Optional[str] = None,
    ):
        """
        reads an optional rate_structure_file and builds a UpdateRequestsFromFile SimulationUpdateFunction


        :param sampling_function: a function to use for sampling requests
        :param rate_structure_file: an optional file for a request rate structure
        :return: a SimulationUpdate function pointing at the first line of a request file
        :raises: an exception if there were issues loading the file
        """
        if rate_structure_file:
            rate_structure_path = Path(rate_structure_file)
            if not rate_structure_path.is_file():
                raise IOError(f"{rate_structure_file} is not a valid path to a request file")
            with open(rate_structure_file, 'r', encoding='utf-8-sig') as rsf:
                reader = DictReader(rsf)
                rate_structure = RequestRateStructure.from_row(next(reader))
        else:
            rate_structure = RequestRateStructure()

        return UpdateRequestsSampling(sampling_function, rate_structure)

    def update(self,
               sim_state: SimulationState,
               env: Environment) -> Tuple[SimulationState, Optional[UpdateRequestsSampling]]:
        """
        add requests based on a sampling function


        :param env: the static environment variables
        :param sim_state: the current sim state
        :return: sim state plus new requests
        """

        new_requests = self.sampling_function(sim_state)
        priced_requests = tuple(r.assign_value(self.rate_structure, sim_state.road_network) for r in new_requests)

        def _add_request(sim: SimulationState, request: Request) -> SimulationState:
            # add request and handle any errors

            error, new_sim = add_request(sim, request)
            if error:
                log.error(error)
                return sim
            return new_sim

        updated_sim = ft.reduce(
            _add_request,
            priced_requests,
            sim_state
        )

        return updated_sim, None
