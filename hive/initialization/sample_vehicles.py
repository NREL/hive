import functools as ft
import logging
import random
from typing import Callable

from returns.result import Result, Failure, Success

from hive.model.entity_position import EntityPosition
from hive.model.roadnetwork.link import Link
from hive.model.roadnetwork.osm.osm_roadnetwork import OSMRoadNetwork
from hive.model.vehicle.vehicle import Vehicle
from hive.runner import Environment
from hive.state.driver_state.autonomous_driver_state.autonomous_available import AutonomousAvailable
from hive.state.driver_state.autonomous_driver_state.autonomous_driver_attributes import AutonomousDriverAttributes
from hive.state.simulation_state.simulation_state import SimulationState
from hive.state.simulation_state.simulation_state_ops import add_vehicle_safe
from hive.state.vehicle_state.idle import Idle
from hive.util import Ratio

log = logging.getLogger(__name__)


def sample_vehicles(
    count: int,
    sim: SimulationState,
    env: Environment,
    location_sampling_function: Callable[[SimulationState], Link],
    soc_sampling_function: Callable[[], Ratio],
    total_seats: int = 4,
    offset: int = 0,
) -> Result[SimulationState, Exception]:
    """
    creates {count} vehicles using the provided sampling functions

    :param count:
    :param sim:
    :param env:
    :param location_sampling_function: samples the initial location for a vehicle
    :param soc_sampling_function: samples the initial state of charge for a vehicle
    :param offset: number to begin counting vehicle ids from (by default, begin counting from zero)
    :return: the updated setup, or, a failure
    """

    mechatronics_id = random.choice(list(env.mechatronics.keys()))
    mechatronics = env.mechatronics.get(mechatronics_id)
    if not mechatronics:
        return Failure(KeyError(f"mechatronics with id {mechatronics_id} not found"))
    else:

        def _add_sample(i: int):
            """
            returns a function which creates the i'th vehicle

            :param i: the number to associate with this sampled vehicle
            :return: a function that adds vehicle i to the SimulationState
            """
            def _inner(s: SimulationState) -> Result[SimulationState, Exception]:
                """
                attempts to add the i'th vehicle to this simulation state

                :param s: the SimulationState to update
                :return: the updated simulation state, or, an exception
                """
                try:
                    vehicle_id = f"v{i}"
                    initial_soc = soc_sampling_function()
                    energy = mechatronics.initial_energy(initial_soc)
                    link = location_sampling_function(s)
                    position = EntityPosition(link.link_id, link.start)
                    vehicle_state = Idle.build(vehicle_id)
                    driver_state = AutonomousAvailable(AutonomousDriverAttributes(vehicle_id))
                    vehicle = Vehicle(id=vehicle_id,
                                      mechatronics_id=mechatronics_id,
                                      energy=energy,
                                      position=position,
                                      vehicle_state=vehicle_state,
                                      driver_state=driver_state,
                                      total_seats=total_seats)
                    add_result = add_vehicle_safe(s, vehicle)
                    return add_result
                except Exception as e:
                    return Failure(e)

            return _inner

        log.info(
            f"sampling vehicles {offset} through {offset + count - 1} ({count} vehicles) with mechatronics id {mechatronics_id}"
        )

        # sample i vehicles, adding each to the sim
        # fail fast if an exception is encountered
        result: Result[SimulationState,
                       Exception] = ft.reduce(lambda acc, i: acc.bind(_add_sample(i)),
                                              range(offset, offset + count), Success(sim))

        return result


def build_default_location_sampling_fn(seed: int = 0) -> Callable[[], Link]:
    """
    constructs a link sampling function that uniformly samples from the provided base locations


    :param bases: the available bases
    :param seed: random seed value
    :return: a link
    """
    random.seed(seed)

    def _inner(sim: SimulationState) -> Link:
        if not isinstance(sim.road_network, OSMRoadNetwork):
            raise NotImplementedError(
                f"this sampling function is only implemented for the OSMRoadNetwork")
        links = list(sim.road_network.link_helper.links.values())
        if len(links) == 0:
            raise AssertionError(f"must have at least one link to sample from")
        random_link = random.choice(links)
        return random_link

    return _inner


def build_default_soc_sampling_fn(lower_bound: Ratio = 1.0,
                                  upper_bound: Ratio = 1.0,
                                  seed: int = 0) -> Callable[[], Ratio]:
    """
    constructs an SoC sampling function that uniformly samples between a lower and upper bound value

    :param lower_bound: the lower bound to sample from
    :param upper_bound: the upper bound to sample from
    :param seed: random seed value
    :return: an SoC value
    """
    assert lower_bound <= upper_bound, ArithmeticError(
        f"lower bound {lower_bound} must be less than or equal to upper bound {upper_bound}")
    assert lower_bound >= 0, ArithmeticError(
        f"lower bound {lower_bound} must be in the range [0, 1]")
    assert lower_bound <= 1, ArithmeticError(
        f"lower bound {lower_bound} must be in the range [0, 1]")
    assert upper_bound >= 0, ArithmeticError(
        f"upper bound {upper_bound} must be in the range [0, 1]")
    assert upper_bound <= 1, ArithmeticError(
        f"upper bound {upper_bound} must be in the range [0, 1]")
    random.seed(seed)

    def _inner() -> Ratio:
        sampled_soc = random.uniform(lower_bound, upper_bound)
        return sampled_soc

    return _inner
