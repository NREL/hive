from __future__ import annotations

import random

from h3 import h3

from hive.dispatcher.forecaster.forecaster_interface import ForecasterInterface
from hive.dispatcher.instruction.instructions import *
from hive.dispatcher.managers.manager_interface import ManagerInterface
from hive.external.demo_base_target.temp_base_target import BaseTarget
from hive.model.energy.charger import Charger
from hive.state.vehicle_state import *
from hive.state.vehicle_state import (
    ReserveBase,
    ChargingBase,
)
from hive.util.helpers import H3Ops

if TYPE_CHECKING:
    from hive.state.simulation_state.simulation_state import SimulationState
    from hive.dispatcher.instruction.instruction_interface import Instruction
    from hive.util.typealiases import Report

log = logging.getLogger(__name__)


def _return_to_base(n, vehicles, simulation_state) -> Tuple[Instruction]:
    instructions = ()

    vehicles.sort(key=lambda v: v.energy_source.soc)

    for i, veh in enumerate(vehicles):
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


def _set_to_reserve(n, vehicles, simulation_state) -> Tuple[Instruction]:
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


def _charge_at_base(n, vehicles, simulation_state) -> Tuple[Instruction]:
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


def _send_vehicle_to_field(n, vehicles, simulation_state) -> Tuple[Instruction]:
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


class DeluxeManager(NamedTuple, ManagerInterface):
    """
    A manager that instructs vehicles on how to behave at the base
    """
    demand_forecaster: ForecasterInterface
    base_target: BaseTarget = BaseTarget()

    def generate_instructions(
            self,
            simulation_state: SimulationState,
    ) -> Tuple[DeluxeManager, Tuple[Instruction, ...], Tuple[Report, ...]]:
        """
        Generate fleet targets for the dispatcher to execute based on the simulation state.

        :param simulation_state: The current simulation state

        :return: the updated Manager along with fleet targets and reports
        """
        updated_forecaster, future_demand = self.demand_forecaster.generate_forecast(simulation_state)

        def is_active(vstate: VehicleState) -> bool:
            return isinstance(vstate, Idle) or \
                   isinstance(vstate, Repositioning)

        instructions = ()

        base_charge_vehicles = [v for v in simulation_state.vehicles.values()
                                if isinstance(v.vehicle_state, ChargingBase)]
        reserve_vehicles = [v for v in simulation_state.vehicles.values()
                            if isinstance(v.vehicle_state, ReserveBase)]
        active_vehicles = [v for v in simulation_state.vehicles.values()
                           if is_active(v.vehicle_state)]

        n_charging = len(base_charge_vehicles)
        n_active = len(active_vehicles)

        charge_target = int(self.base_target.get_target(simulation_state.sim_time))
        active_target = future_demand.value

        charge_diff = charge_target - n_charging
        active_diff = active_target - n_active

        if active_diff < 0:
            # we have more active vehicles than we need
            if charge_diff < 0:
                # we have more charging vehicles than we need
                # ACTION: send active vehicles to base, send charging vehicles to reserve
                active_instructions = _return_to_base(abs(active_diff), active_vehicles, simulation_state)
                reserve_instructions = _set_to_reserve(abs(charge_diff), base_charge_vehicles, simulation_state)
                instructions = instructions + active_instructions + reserve_instructions
            elif charge_diff > 0:
                # we don't have enough charging vehicles
                # ACTION: take reserve and charge them, send active vehicles to base
                active_instructions = _return_to_base(abs(active_diff), active_vehicles, simulation_state)
                charge_instructions = _charge_at_base(abs(charge_diff), reserve_vehicles, simulation_state)
                instructions = instructions + active_instructions + charge_instructions
            else:
                # ACTION: just send active vehicles home
                active_instructions = _return_to_base(abs(active_diff), active_vehicles, simulation_state)
                instructions = instructions + active_instructions
        elif active_diff > 0:
            # we need more vehicles in the field
            if charge_diff < 0:
                # we have more charging vehicles than we need
                # ACTION: send highest soc vehicles out to field
                repos_instructions = _send_vehicle_to_field(active_diff, base_charge_vehicles, simulation_state)
                instructions = instructions + repos_instructions
            elif charge_diff > 0:
                # we don't have enough charging vehicles
                # ACTION: send vehicles to field first then charge remaining vehicles
                charge_instructions = _charge_at_base(charge_diff, reserve_vehicles, simulation_state)
                repos_instructions = _send_vehicle_to_field(active_diff, reserve_vehicles, simulation_state)
                instructions = instructions + charge_instructions + repos_instructions
            else:
                repos_instructions = _send_vehicle_to_field(active_diff, reserve_vehicles, simulation_state)
                instructions = instructions + repos_instructions

        return self._replace(demand_forecaster=updated_forecaster), instructions, ()
