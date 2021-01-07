import random
from typing import Tuple

from hive.model.request import Request
from hive.runner import Environment
from hive.state.simulation_state.simulation_state import SimulationState


def default_request_sampler(
        count: int,
        simulation_state: SimulationState,
        environment: Environment,
) -> Tuple[Request, ...]:
    """
    samples `count` requests uniformly across time and space

    :param count: the number of requests to sample
    :param simulation_state: the simulation state
    :param environment: the environment

    :return: a tuple of the sampled requests
    """

    requests = []

    possible_timesteps = list(range(
        int(environment.config.sim.start_time),
        int(environment.config.sim.end_time),
        environment.config.sim.timestep_duration_seconds,
    ))

    id_counter = 0
    while len(requests) < count:
        random_source_link = simulation_state.road_network.random_link()
        random_destination_link = simulation_state.road_network.random_link()

        if random_source_link.link_id == random_destination_link.link_id:
            continue

        request = Request.build(
            request_id="r" + str(id_counter),
            origin=random_source_link.start,
            destination=random_destination_link.end,
            road_network=simulation_state.road_network,
            departure_time=random.choice(possible_timesteps),
            passengers=random.choice([1, 2, 3, 4]),
        )

        requests.append(request)

    sorted_reqeusts = sorted(requests, key=lambda r: r.departure_time)

    return tuple(sorted_reqeusts)
