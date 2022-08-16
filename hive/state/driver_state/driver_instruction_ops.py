from __future__ import annotations

import logging
from typing import Optional, TYPE_CHECKING

import h3

from hive.dispatcher.instruction.instruction import Instruction
from hive.dispatcher.instruction.instructions import (
    ChargeBaseInstruction,
    DispatchBaseInstruction,
    IdleInstruction,
    RepositionInstruction,
)
from hive.model.roadnetwork.link import Link
from hive.dispatcher.instruction_generator.instruction_generator_ops import (
    instruct_vehicles_to_dispatch_to_station,
    get_nearest_valid_station_distance,
)
from hive.util import TupleOps, H3Ops
from hive.model.energy.energytype import EnergyType
from hive.model.roadnetwork.route import route_distance_km

if TYPE_CHECKING:
    from hive.state.simulation_state.simulation_state import SimulationState
    from hive.runner.environment import Environment
    from hive.model.vehicle.vehicle import Vehicle
    from hive.model.base import Base
    from hive.util.typealiases import GeoId, BaseId

log = logging.getLogger(__name__)


def human_charge_at_home(
        veh: Vehicle,
        home_base: Base,
        sim: SimulationState,
        env: Environment,
) -> Optional[ChargeBaseInstruction]:
    """
    Attempts to charge at home using the lowest power charger

    :param veh:
    :param home_base:
    :param sim:
    :param env:
    :return: 
    """

    my_station = sim.stations.get(home_base.station_id)
    my_mechatronics = env.mechatronics.get(veh.mechatronics_id)

    if not my_station:
        log.error(f"could not find station {home_base.station_id} for home_base {home_base.id}")
        return None
    elif my_mechatronics.is_full(veh):
        return None

    chargers = tuple(filter(
        lambda c: my_mechatronics.valid_charger(c),
        [env.chargers[cid] for cid in my_station.state.keys()]
    ))
    if not chargers:
        return None
    else:
        # take the lowest power charger
        charger = sorted(chargers, key=lambda c: c.rate)[0]
        return ChargeBaseInstruction(veh.id, home_base.id, charger.id)


def human_go_home(
        veh: Vehicle,
        home_base: Base,
        sim: SimulationState,
        env: Environment,
) -> Optional[Instruction]:
    """
    human drivers go home at the end of their shift.
    edge case: vehicles may not have enough remaining range to
    reach their home from their current location.

    :param veh: the vehicle ending their shift
    :param home_base: the vehicle's home
    :param sim: the current simulation state
    :param env: the environment for this simulation
    :return: the instruction for this driver
    """
    mechatronics = env.mechatronics.get(veh.mechatronics_id)
    remaining_range = mechatronics.range_remaining_km(veh) if mechatronics else None
    if not remaining_range:
        return None
    else:
        required_range = sim.road_network.distance_by_geoid_km(veh.geoid, home_base.geoid)
        if (home_base.station_id is None) and (EnergyType.ELECTRIC in veh.energy):
            # no charger at home, need enough charge to make it to a station in the morning
            required_range += get_nearest_valid_station_distance(
                max_search_radius_km=env.config.dispatcher.max_search_radius_km,
                vehicle=veh,
                geoid=home_base.geoid,
                simulation_state=sim,
                environment=env,
                target_soc=env.config.dispatcher.ideal_fastcharge_soc_limit,
                charging_search_type=env.config.dispatcher.charging_search_type
            )

            target_soc = mechatronics.calc_required_soc(required_range +
                                                        env.config.dispatcher.charging_range_km_threshold)
        else:
            target_soc = env.config.dispatcher.ideal_fastcharge_soc_limit

        if required_range < remaining_range:
            # has enough remaining range to make it home sweet home (and possibly a station in the morning)
            instruction = DispatchBaseInstruction(veh.id, home_base.id)
            return instruction
        else:
            # needs to go charge on the way home
            charge_instructions = instruct_vehicles_to_dispatch_to_station(
                n=1,
                max_search_radius_km=env.config.dispatcher.max_search_radius_km,
                vehicles=(veh,),
                simulation_state=sim,
                environment=env,
                target_soc=target_soc,
                charging_search_type=env.config.dispatcher.charging_search_type
            )

            return TupleOps.head_optional(charge_instructions)


def human_look_for_requests(
        veh: Vehicle,
        sim: SimulationState,
) -> Optional[RepositionInstruction]:
    """
    Human driver relocates in search of greener request pastures.

    :param veh:
    :param sim:
    :return:
    """

    def _get_reposition_location() -> Optional[Link]:
        """
        takes the most dense request search hex as a proxy for high demand areas
        :return:
        """
        if len(sim.r_search) == 0:
            # no requests in system, do nothing
            return None
        else:
            # find the most dense request search hex and sends vehicles to the center
            best_search_hex = sorted(
                [(k, len(v)) for k, v in sim.r_search.items()], key=lambda t: t[1],
                reverse=True
            )[0][0]
        destination = h3.h3_to_center_child(best_search_hex, sim.sim_h3_location_resolution)
        destination_link = sim.road_network.position_from_geoid(destination)
        return destination_link

    dest = _get_reposition_location()
    if dest:
        return RepositionInstruction(veh.id, dest.link_id)
    else:
        return None


def idle_if_at_soc_limit(
        veh: Vehicle,
        env: Environment,
) -> Optional[IdleInstruction]:
    """
    Generates an IdleInstruction if the vehicle soc is above the limit set by 
    env.config.dispatcher.ideal_fastcharge_soc_limit

    :param veh:
    :param env:
    :return: 
    """
    mechatronics = env.mechatronics.get(veh.mechatronics_id)
    battery_soc = mechatronics.fuel_source_soc(veh)
    if battery_soc >= env.config.dispatcher.ideal_fastcharge_soc_limit:
        return IdleInstruction(veh.id)


def av_charge_base_instruction(
        veh: Vehicle,
        sim: SimulationState,
        env: Environment,
) -> Optional[ChargeBaseInstruction]:
    """
    Autonomous vehicles will attempt to charge at the base until they reach full energy capacity
    
    :param veh:
    :param sim:
    :param env:
    :return: 
    """

    my_base = sim.bases.get(veh.vehicle_state.base_id)
    my_mechatronics = env.mechatronics.get(veh.mechatronics_id)
    if not my_base:
        return None
    elif not my_base.station_id:
        return None
    elif not my_mechatronics:
        return None
    elif my_mechatronics.is_full(veh):
        return None

    my_station = sim.stations.get(my_base.station_id)
    if not my_station:
        log.error(f"could not find station {my_base.station_id} for base {my_base.base_id}")
        return None

    chargers = tuple(filter(
        lambda c: my_mechatronics.valid_charger(c),
        [cs.charger for cs in my_station.state.values()]
    ))

    if not chargers:
        return None

    # take the lowest power charger
    charger = sorted(chargers, key=lambda c: c.rate)[0]
    return ChargeBaseInstruction(veh.id, my_base.id, charger.id)


def av_dispatch_base_instruction(
        veh: Vehicle,
        sim: SimulationState,
        env: Environment,
) -> Optional[DispatchBaseInstruction]:
    """
    Autonomous vehicles will return to a base after 10 minutes of being idle;
    They find the nearest base that they are a member of

    :param veh:
    :param sim:
    :param env:
    :return:
    """
    if veh.vehicle_state.idle_duration > env.config.dispatcher.idle_time_out_seconds:
        # timeout after being idle too long

        def valid_fn(base: Base) -> bool:
            vehicle_has_access = base.membership.grant_access_to_membership(veh.membership)
            return vehicle_has_access

        best_base = H3Ops.nearest_entity_by_great_circle_distance(
            geoid=veh.geoid,
            entities=sim.bases.values(),
            entity_search=sim.b_search,
            is_valid=valid_fn,
            sim_h3_search_resolution=sim.sim_h3_search_resolution,
            max_search_distance_km=env.config.dispatcher.max_search_radius_km,
        )

        if best_base:
            return DispatchBaseInstruction(veh.id, best_base.id)

    return None
