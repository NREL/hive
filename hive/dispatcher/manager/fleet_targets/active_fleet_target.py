from __future__ import annotations

import random
from typing import TYPE_CHECKING, NamedTuple, Callable

import immutables
from h3 import h3

from hive.dispatcher.instruction import RepositionInstruction, DispatchBaseInstruction
from hive.dispatcher.manager.fleet_targets.fleet_target_interface import FleetTarget
from hive.state.vehicle_state import *
from hive.util.helpers import H3Ops, DictOps

if TYPE_CHECKING:
    from hive.dispatcher.instruction.instruction_interface import InstructionMap
    from hive.model.roadnetwork.roadnetwork import RoadNetwork
    from hive.util.typealiases import GeoId
    from hive.state.simulation_state.simulation_state import SimulationState

random.seed(123)


class ActiveFleetTarget(NamedTuple, FleetTarget):
    """
    a fleet target for how many vehicles are active in the field
    """
    n_active_vehicles: int
    is_active: Callable[[VehicleState], bool]

    @staticmethod
    def _sample_random_location(road_network: RoadNetwork) -> GeoId:
        random_hex = random.choice(tuple(road_network.geofence.geofence_set))
        children = h3.h3_to_children(random_hex, road_network.sim_h3_resolution)
        return children.pop()

    def apply_target(self, sim_state: SimulationState) -> InstructionMap:
        """
        generates dispatcher instructions based on a specific simulation state

        :param sim_state: the state of the simulation

        :return: a set of instructions mapped to a specific vehicle
        """
        fleet_state_instructions = immutables.Map()

        # only generate instructions on 15 minute intervals
        if sim_state.sim_time % (15 * 60) != 0:
            return fleet_state_instructions

        active_vehicles = [v for v in sim_state.vehicles.values()
                           if self.is_active(v.vehicle_state)]
        n_active = len(active_vehicles)
        active_diff = n_active - self.n_active_vehicles

        def is_base_state(vstate):
            return isinstance(vstate, ChargingBase) or isinstance(vstate, ReserveBase)

        def is_non_interrupt_state(vstate):
            return isinstance(vstate, DispatchStation) \
                   or isinstance(vstate, ChargingStation) \
                   or isinstance(vstate, ServicingTrip)

        if active_diff < 0:
            # we need abs(active_diff) more vehicles in service to meet demand
            base_vehicles = [v for v in sim_state.vehicles.values() if is_base_state(v.vehicle_state)]
            for i, veh in enumerate(base_vehicles):
                if i + 1 > abs(active_diff):
                    break
                random_location = self._sample_random_location(sim_state.road_network)
                instruction = RepositionInstruction(vehicle_id=veh.id, destination=random_location)
                fleet_state_instructions = DictOps.add_to_dict(fleet_state_instructions, veh.id, instruction)

        elif active_diff > 0:
            # we can remove active_diff vehicles from service
            for i, veh in enumerate(active_vehicles):
                if i + 1 > active_diff:
                    break
                elif is_non_interrupt_state(veh.vehicle_state):
                    continue

                nearest_base = H3Ops.nearest_entity(geoid=veh.geoid,
                                                    entities=sim_state.bases,
                                                    entity_search=sim_state.b_search,
                                                    sim_h3_search_resolution=sim_state.sim_h3_search_resolution)
                if nearest_base:
                    instruction = DispatchBaseInstruction(
                        vehicle_id=veh.id,
                        base_id=nearest_base.id,
                    )

                    fleet_state_instructions = DictOps.add_to_dict(fleet_state_instructions, veh.id, instruction)
                else:
                    # user set the max search radius too low
                    continue

        return fleet_state_instructions
