from __future__ import annotations

import logging
from typing import Optional, TYPE_CHECKING, Tuple

import h3

from nrel.hive.dispatcher.instruction.instruction import Instruction
from nrel.hive.dispatcher.instruction.instructions import (
    ChargeBaseInstruction,
    DispatchBaseInstruction,
    IdleInstruction,
    RepositionInstruction,
)
from nrel.hive.dispatcher.instruction_generator.instruction_generator_ops import (
    instruct_vehicles_to_dispatch_to_station,
)
from nrel.hive.model.energy.energytype import EnergyType
from nrel.hive.model.entity import Entity
from nrel.hive.state.vehicle_state.charging_base import ChargingBase
from nrel.hive.state.vehicle_state.idle import Idle
from nrel.hive.state.vehicle_state.reserve_base import ReserveBase
from nrel.hive.util import TupleOps, H3Ops
from nrel.hive.util.dict_ops import DictOps

if TYPE_CHECKING:
    from nrel.hive.state.simulation_state.simulation_state import SimulationState
    from nrel.hive.runner.environment import Environment
    from nrel.hive.model.vehicle.vehicle import Vehicle
    from nrel.hive.model.base import Base
    from nrel.hive.model.energy.charger import Charger
    from nrel.hive.model.entity_position import EntityPosition

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

    if home_base.station_id is None:
        # can't charge at home, no station
        return None

    my_station = sim.stations.get(home_base.station_id)
    my_mechatronics = env.mechatronics.get(veh.mechatronics_id)

    if my_mechatronics is None:
        log.error(f"no mechatronics {veh.mechatronics_id} found for vehicle {veh.id}")
        return None

    if not my_station:
        log.error(f"could not find station {home_base.station_id} for home_base {home_base.id}")
        return None
    elif my_mechatronics.is_full(veh):
        return None

    chargers = tuple(
        filter(
            my_mechatronics.valid_charger,
            [env.chargers[cid] for cid in sorted(my_station.state.keys())],
        )
    )
    if not chargers:
        return None
    else:
        # take the lowest power charger
        charger: Charger = sorted(chargers, key=lambda c: (c.rate, c.id))[0]
        return ChargeBaseInstruction(veh.id, home_base.id, charger.id)


def human_go_home(
    veh: Vehicle,
    home_base: Base,
    sim: SimulationState,
    env: Environment,
) -> Optional[Instruction]:
    """
    Human drivers go home at the end of their shift.
    For drivers can't make it home without charging, or, drivers without home charging,
    they charge at the end of the shift to the config.dispatcher.human_driver_off_shift_charge_target

    :param veh: the vehicle ending their shift
    :param home_base: the vehicle's home
    :param sim: the current simulation state
    :param env: the environment for this simulation
    :return: the instruction for this driver
    """
    mechatronics = env.mechatronics.get(veh.mechatronics_id)
    if mechatronics is None:
        log.error(f"no mechatronics {veh.mechatronics_id} found for vehicle {veh.id}")
        return None

    remaining_range = mechatronics.range_remaining_km(veh) if mechatronics else None
    if not remaining_range:
        return None

    # lets check if the driver can make it home without running out of energy
    required_range = sim.road_network.distance_by_geoid_km(veh.geoid, home_base.geoid)
    cant_make_it_home = required_range >= remaining_range

    # lets also check if the driver if the driver has home charging
    no_home_charging = (home_base.station_id is None) and (EnergyType.ELECTRIC in veh.energy)

    if cant_make_it_home or no_home_charging:
        # vehicle needs to charge on the way home
        charge_instructions = instruct_vehicles_to_dispatch_to_station(
            n=1,
            max_search_radius_km=env.config.dispatcher.max_search_radius_km,
            vehicles=(veh,),
            simulation_state=sim,
            environment=env,
            target_soc=env.config.dispatcher.human_driver_off_shift_charge_target,
            charging_search_type=env.config.dispatcher.charging_search_type,
        )
        return TupleOps.head_optional(charge_instructions)
    else:
        # has enough remaining range to make it home sweet home
        instruction = DispatchBaseInstruction(veh.id, home_base.id)
        return instruction


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

    def _get_reposition_location() -> Optional[EntityPosition]:
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
                [(k, len(v)) for k, v in sim.r_search.items()],
                key=lambda t: (t[1], t[0]),  # fallback to geoid (index 0) to break ties
                reverse=True,
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
    if mechatronics is None:
        log.error(f"no mechatronics {veh.mechatronics_id} found for vehicle {veh.id}")
        return None

    battery_soc = mechatronics.fuel_source_soc(veh)
    if battery_soc >= env.config.dispatcher.ideal_fastcharge_soc_limit:
        return IdleInstruction(veh.id)

    return None


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
    base_state = veh.vehicle_state
    if not isinstance(base_state, (ReserveBase, ChargingBase)):
        # this instruction is only valid for these two states
        return None

    my_base = sim.bases.get(base_state.base_id)
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
        log.error(f"could not find station {my_base.station_id} for base {my_base.id}")
        return None

    chargers: Tuple[Charger, ...] = tuple(
        filter(
            my_mechatronics.valid_charger,
            [cs.charger for cs in sorted(my_station.state.values(), key=lambda c: c.id)],
        )
    )

    if not chargers:
        return None

    # take the lowest power charger
    charger: Charger = sorted(chargers, key=lambda c: (c.rate, c.id))[0]
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
    idle_state = veh.vehicle_state

    if not isinstance(idle_state, Idle):
        # this instruction is only valid for idle state
        return None

    if idle_state.idle_duration > env.config.dispatcher.idle_time_out_seconds:
        # timeout after being idle too long

        def valid_fn(base: Entity) -> bool:
            vehicle_has_access = base.membership.grant_access_to_membership(veh.membership)
            return vehicle_has_access

        best_base = H3Ops.nearest_entity_by_great_circle_distance(
            geoid=veh.geoid,
            entities=sim.get_bases(),
            entity_search=sim.b_search,
            is_valid=valid_fn,
            sim_h3_search_resolution=sim.sim_h3_search_resolution,
            max_search_distance_km=env.config.dispatcher.max_search_radius_km,
        )

        if best_base:
            return DispatchBaseInstruction(veh.id, best_base.id)

    return None
