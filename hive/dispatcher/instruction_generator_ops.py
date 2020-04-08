from __future__ import annotations

import random
from typing import List

from h3 import h3

from hive.dispatcher.instruction.instructions import *
from hive.util.helpers import H3Ops

if TYPE_CHECKING:
    from hive.model.vehicle.vehicle import Vehicle
    from hive.state.simulation_state.simulation_state import SimulationState

random.seed(123)


def return_to_base(n: int, vehicles: List[Vehicle], simulation_state: SimulationState) -> Tuple[Instruction]:
    """
    a helper function to send n vehicles back to the base

    :param n: how many vehicles to send back to base
    :param vehicles: the list of vehicles to consider
    :param simulation_state: the simulation state
    :return:
    """

    instructions = ()

    vehicles.sort(key=lambda v: v.energy_source.soc)

    for veh in vehicles:
        if len(instructions) >= n:
            break

        nearest_base = H3Ops.nearest_entity(geoid=veh.geoid,
                                            entities=simulation_state.bases,
                                            entity_search=simulation_state.b_search,
                                            sim_h3_search_resolution=simulation_state.sim_h3_search_resolution)
        if nearest_base:
            instruction = DispatchBaseInstruction(
                vehicle_id=veh.id,
                base_id=nearest_base.id,
            )

            instructions = instructions + (instruction,)
        else:
            # user set the max search radius too low
            continue

    return instructions


def set_to_reserve(n: int, vehicles: List[Vehicle], simulation_state: SimulationState) -> Tuple[Instruction]:
    """
    a helper function to set n vehicles to reserve at the base

    :param n: how many vehicles to set to reserve
    :param vehicles: the list of vehicles to consider
    :param simulation_state: the simulation state
    :return:
    """
    instructions = ()

    vehicles.sort(key=lambda v: v.energy_source.soc, reverse=True)

    for veh in vehicles:
        if len(instructions) >= n:
            break

        base_id = simulation_state.b_locations[veh.geoid]
        instruction = ReserveBaseInstruction(
            vehicle_id=veh.id,
            base_id=base_id,
        )

        instructions = instructions + (instruction,)

    return instructions


def charge_at_base(n: int, vehicles: List[Vehicle], simulation_state: SimulationState) -> Tuple[Instruction]:
    """
    a helper function to set n vehicles to charge at the base

    :param n: how many vehicles to charge at the base
    :param vehicles: the list of vehicles to consider
    :param simulation_state: the simulation state
    :return:
    """
    instructions = ()

    vehicles.sort(key=lambda v: v.energy_source.soc)

    for veh in vehicles:
        if len(instructions) >= n:
            break
        base_id = simulation_state.b_locations[veh.geoid]
        base = simulation_state.bases[base_id]
        if base.station_id:
            instruction = ChargeBaseInstruction(
                vehicle_id=veh.id,
                base_id=base.id,
                charger=Charger.LEVEL_2,
            )

            instructions = instructions + (instruction,)

    return instructions


def send_vehicle_to_field(n: int, vehicles: List[Vehicle], simulation_state: SimulationState) -> Tuple[Instruction]:
    """
    a helper function to send n vehicles into the field at a random location

    :param n: how many vehicles to send to the field
    :param vehicles: the list of vehicles to consider
    :param simulation_state: the simulation state
    :return:
    """

    def _sample_random_location(road_network) -> GeoId:
        random_hex = random.choice(tuple(road_network.geofence.geofence_set))
        children = h3.h3_to_children(random_hex, road_network.sim_h3_resolution)
        return children.pop()

    instructions = ()

    vehicles.sort(key=lambda v: v.energy_source.soc, reverse=True)

    for veh in vehicles:
        if len(instructions) >= n:
            break
        random_location = _sample_random_location(simulation_state.road_network)
        instruction = RepositionInstruction(vehicle_id=veh.id, destination=random_location)
        instructions = instructions + (instruction,)

    return instructions
