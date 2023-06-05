import random
from typing import Tuple, List

from nrel.hive.model.request import Request
from nrel.hive.model.roadnetwork.osm.osm_roadnetwork import OSMRoadNetwork
from nrel.hive.model.sim_time import SimTime
from nrel.hive.runner import Environment
from nrel.hive.state.simulation_state.simulation_state import SimulationState


def default_request_sampler(
    count: int,
    simulation_state: SimulationState,
    environment: Environment,
    allow_pooling: bool = False,
    random_seed: int = 0,
) -> Tuple[Request, ...]:
    """
    samples `count` requests uniformly across time and space

    :param count: the number of requests to sample
    :param simulation_state: the simulation state
    :param environment: the environment
    :param random_seed: the random seed used for the random selections

    :return: a tuple of the sampled requests
    """
    if not isinstance(simulation_state.road_network, OSMRoadNetwork):
        raise NotImplementedError("request sampling is only implemented for the OSMRoadNetwork")

    if simulation_state.road_network.link_helper is None:
        raise Exception("Expected link helper on OSMRoadNetwork but found None")

    random.seed(random_seed)

    requests: List[Request] = []

    possible_timesteps = list(
        range(
            int(environment.config.sim.start_time),
            int(environment.config.sim.end_time),
            environment.config.sim.timestep_duration_seconds,
        )
    )
    possible_links = list(simulation_state.road_network.link_helper.links.values())

    id_counter = 0
    while len(requests) < count:
        random_source_link = random.choice(possible_links)
        random_destination_link = random.choice(possible_links)

        if random_source_link.start == random_destination_link.end:
            # skip if the request starts and ends at the same location
            continue

        request = Request.build(
            request_id="r" + str(id_counter),
            origin=random_source_link.start,
            destination=random_destination_link.end,
            road_network=simulation_state.road_network,
            departure_time=SimTime(random.choice(possible_timesteps)),
            passengers=random.choice([1, 2, 3, 4]),
            allows_pooling=allow_pooling,
        )

        requests.append(request)

        id_counter += 1

    sorted_reqeusts = sorted(requests, key=lambda r: (r.departure_time, r.id))

    return tuple(sorted_reqeusts)
