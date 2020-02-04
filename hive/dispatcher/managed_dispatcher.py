from __future__ import annotations
from typing import Tuple, NamedTuple

import json
import random

from pkg_resources import resource_filename
from h3 import h3

from hive.model.instruction import *
from hive.dispatcher.manager.manager_interface import ManagerInterface
from hive.dispatcher.manager.fleet_target import FleetStateTarget
from hive.state.simulation_state import SimulationState
from hive.model.vehiclestate import VehicleState
from hive.model.vehicle import Vehicle
from hive.model.energy.charger import Charger
from hive.dispatcher.dispatcher_interface import DispatcherInterface
from hive.util.helpers import H3Ops
from hive.util.typealiases import GeoId, VehicleId


class ManagedDispatcher(NamedTuple, DispatcherInterface):
    """
    This dispatcher greedily assigns requests and reacts to the fleet targets set by the fleet manager.
    """
    manager: ManagerInterface
    geofence: list
    LOW_SOC_TRESHOLD: float = 0.2

    @classmethod
    def build(cls,
              manager: ManagerInterface,
              geofence_file: str,
              low_soc_threshold: float = 0.2) -> ManagedDispatcher:

        with open(resource_filename("hive.resources.geofence", geofence_file)) as f:
            geojson = json.load(f)
            geofence = list(h3.polyfill(
                geo_json=geojson['features'][0]['geometry'],
                res=10,
                geo_json_conformant=True))
            return ManagedDispatcher(
                manager=manager,
                geofence=geofence,
                LOW_SOC_TRESHOLD=low_soc_threshold
            )

    def _sample_random_location(self, sim_state_resolution: int) -> GeoId:
        # TODO: replace with geofence from road network once implemented
        random_hex = random.choice(self.geofence)
        children = h3.h3_to_children(random_hex, sim_state_resolution)
        return children.pop()

    def _handle_fleet_targets(
            self,
            fleet_state_target: FleetStateTarget,
            simulation_state: SimulationState,
            vehicle_ids_given_instructions: Tuple[VehicleId, ...],
    ) -> Tuple[Instruction, ...]:

        fleet_state_instructions = ()
        active_target = fleet_state_target['ACTIVE']
        active_vehicles = [v for v in simulation_state.vehicles.values()
                           if v.vehicle_state in active_target.state_set
                           and v.id not in vehicle_ids_given_instructions]
        n_active = len(active_vehicles)
        active_diff = n_active - active_target.n_vehicles
        _base_states = (
            VehicleState.CHARGING_BASE,
            VehicleState.RESERVE_BASE,
        )
        if active_diff < 0:
            # we need abs(active_diff) more vehicles in service to meet demand
            base_vehicles = [v for v in simulation_state.vehicles.values()
                             if v.vehicle_state in _base_states
                             and v.id not in vehicle_ids_given_instructions]
            for i, veh in enumerate(base_vehicles):
                if i + 1 > abs(active_diff):
                    break
                random_location = self._sample_random_location(simulation_state.sim_h3_location_resolution)
                instruction = RepositionInstruction(vehicle_id=veh.id, destination=random_location)
                fleet_state_instructions = fleet_state_instructions + (instruction,)
                vehicle_ids_given_instructions = vehicle_ids_given_instructions + (veh.id,)
        elif active_diff > 0:
            # we can remove active_diff vehicles from service
            non_interrupt_states = (
                VehicleState.DISPATCH_STATION,
                VehicleState.CHARGING_STATION,
                VehicleState.SERVICING_TRIP,
            )
            for i, veh in enumerate(active_vehicles):
                if i + 1 > active_diff:
                    break
                elif veh.vehicle_state in non_interrupt_states:
                    continue

                nearest_base = H3Ops.nearest_entity(geoid=veh.geoid,
                                                    entities=simulation_state.bases,
                                                    entity_search=simulation_state.b_search,
                                                    sim_h3_search_resolution=simulation_state.sim_h3_search_resolution)
                if nearest_base:
                    instruction = DispatchBaseInstruction(
                        vehicle_id=veh.id,
                        destination=nearest_base.geoid,
                    )
                    fleet_state_instructions = fleet_state_instructions + (instruction,)
                    vehicle_ids_given_instructions = vehicle_ids_given_instructions + (veh.id,)
                else:
                    # user set the max search radius too low
                    continue

        return fleet_state_instructions

    def generate_instructions(self,
                              simulation_state: SimulationState,
                              ) -> Tuple[DispatcherInterface, Tuple[Instruction, ...]]:
        # TODO: a lot of this code is shared between greedy dispatcher and managed dispatcher. Plus, it's getting
        #  too large. Should probably refactor.
        instructions = ()
        vehicle_ids_given_instructions = ()

        # 1. find vehicles that require charging
        low_soc_vehicles = [v for v in simulation_state.vehicles.values()
                            if v.energy_source.soc <= self.LOW_SOC_TRESHOLD
                            and v.vehicle_state != VehicleState.DISPATCH_STATION]
        nearest_station = None
        for veh in low_soc_vehicles:
            nearest_station = H3Ops.nearest_entity(geoid=veh.geoid,
                                                   entities=simulation_state.stations,
                                                   entity_search=simulation_state.s_search,
                                                   sim_h3_search_resolution=simulation_state.sim_h3_search_resolution,
                                                   is_valid=lambda s: s.has_available_charger(Charger.DCFC))
            if nearest_station:
                instruction = DispatchStationInstruction(
                    vehicle_id=veh.id,
                    station_id=nearest_station.id,
                    charger=Charger.DCFC,
                )

                instructions = instructions + (instruction,)
                vehicle_ids_given_instructions = vehicle_ids_given_instructions + (veh.id,)
            else:
                # user set the max search radius too low (should really be computed by
                # HIVE based on the RoadNetwork at initialization anyway)
                # also possible: no charging stations available. implement a queueing solution
                # for agents who could wait to charge
                continue

        def _is_valid_for_dispatch(vehicle: Vehicle) -> bool:
            _valid_states = (VehicleState.IDLE,
                             VehicleState.CHARGING_BASE,
                             VehicleState.RESERVE_BASE,
                             VehicleState.DISPATCH_BASE)
            return bool(vehicle.id not in vehicle_ids_given_instructions and
                        vehicle.energy_source.soc > self.LOW_SOC_TRESHOLD and
                        vehicle.vehicle_state in _valid_states)

        # 2. find requests that need a vehicle. Sorted by price high to low
        unassigned_requests = sorted(
            [r for r in simulation_state.requests.values() if not r.dispatched_vehicle],
            key=lambda r: r.value,
            reverse=True,
        )
        for request in unassigned_requests:
            nearest_vehicle = H3Ops.nearest_entity(geoid=request.origin,
                                                   entities=simulation_state.vehicles,
                                                   entity_search=simulation_state.v_search,
                                                   sim_h3_search_resolution=simulation_state.sim_h3_search_resolution,
                                                   is_valid=_is_valid_for_dispatch)
            if nearest_vehicle:
                instruction = DispatchTripInstruction(
                    vehicle_id=nearest_vehicle.id,
                    request_id=request.id,
                )

                instructions = instructions + (instruction,)
                vehicle_ids_given_instructions = vehicle_ids_given_instructions + (nearest_vehicle.id,)

        # 3. try to meet active target set by fleet manager in 15 minute intervals
        if simulation_state.sim_time % 900 == 0:
            _, fleet_state_target = self.manager.generate_fleet_target(simulation_state)
            fleet_state_instructions = self._handle_fleet_targets(
                fleet_state_target,
                simulation_state,
                vehicle_ids_given_instructions,
            )
            instructions = instructions + fleet_state_instructions

        def _should_base_charge(vehicle: Vehicle) -> bool:
            return bool(vehicle.vehicle_state == VehicleState.RESERVE_BASE and not
            vehicle.energy_source.is_at_ideal_energy_limit())

        # 4. charge vehicles sitting at base
        base_charge_vehicles = [v for v in simulation_state.vehicles.values() if
                                v.id not in vehicle_ids_given_instructions and _should_base_charge(v)]
        for v in base_charge_vehicles:
            base_id = simulation_state.b_locations[v.geoid][0]
            base = simulation_state.bases[base_id]
            if base.station_id:
                instruction = ChargeBaseInstruction(
                    vehicle_id=v.id,
                    station_id=base.station_id,
                    charger=Charger.LEVEL_2,
                )
                instructions = instructions + (instruction,)

        return self, instructions
