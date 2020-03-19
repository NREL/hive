from __future__ import annotations

from typing import NamedTuple, Optional, TYPE_CHECKING, Tuple

from hive.model.vehicle.vehicle_state import *
from hive.util.exception import SimulationStateError

from hive.runner.environment import Environment

from hive.model.instruction.instruction_interface import Instruction
from hive.model.vehicle.vehiclestate import VehicleState
from hive.util.typealiases import StationId, VehicleId, RequestId, GeoId
from hive.model.energy.charger import Charger
from hive.state import entity_state

import logging

log = logging.getLogger(__name__)

if TYPE_CHECKING:
    from hive.state.simulation_state import SimulationState


class DispatchTripInstruction(NamedTuple, Instruction):
    vehicle_id: VehicleId
    request_id: RequestId

    def apply_instruction(self,
                          sim_state: SimulationState,
                          env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        vehicle = sim_state.vehicles.get(self.vehicle_id)
        request = sim_state.requests.get(self.request_id)
        if not vehicle:
            return SimulationStateError(f"vehicle {vehicle} not found"), None
        elif not request:
            return SimulationStateError(f"request {request} not found"), None
        else:
            start = vehicle.geoid
            end = request.origin
            route = sim_state.road_network.route(start, end)
            prev_state = vehicle.vehicle_state
            next_state = DispatchTrip(self.vehicle_id, self.request_id, route)
            return entity_state.transition(sim_state, env, prev_state, next_state)


class ServeTripInstruction(NamedTuple, Instruction):
    vehicle_id: VehicleId
    request_id: RequestId

    def apply_instruction(self,
                          sim_state: SimulationState,
                          env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        vehicle = sim_state.vehicles.get(self.vehicle_id)
        request = sim_state.requests.get(self.request_id)
        if not vehicle:
            return SimulationStateError(f"vehicle {vehicle} not found"), None
        elif not request:
            return SimulationStateError(f"request {request} not found"), None
        else:
            start = request.origin
            end = request.destination
            route = sim_state.road_network.route(start, end)
            prev_state = vehicle.vehicle_state
            next_state = ServicingTrip(self.vehicle_id, self.request_id, route, request.passengers)
            return entity_state.transition(sim_state, env, prev_state, next_state)


class DispatchStationInstruction(NamedTuple, Instruction):
    vehicle_id: VehicleId
    station_id: StationId
    charger: Charger

    def apply_instruction(self,
                          sim_state: SimulationState,
                          env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        vehicle = sim_state.vehicles.get(self.vehicle_id)
        station = sim_state.stations.get(self.station_id)
        if not vehicle:
            return SimulationStateError(f"vehicle {vehicle} not found"), None
        elif not station:
            return SimulationStateError(f"station {station} not found"), None
        else:
            start = vehicle.geoid
            end = station.geoid
            route = sim_state.road_network.route(start, end)
            prev_state = vehicle.vehicle_state
            next_state = DispatchStation(self.vehicle_id, self.station_id, route, self.charger)
            return entity_state.transition(sim_state, env, prev_state, next_state)

# todo: here.
#  follow the pattern. an Instruction is the supposed interface between the dispatcher and the simulation
#  it feels a little redundant to the VehicleState refactor. the main difference is the Instruction seems
#  to be the place where a Route is calculated. in particular, the apply_instruction method pretty much
#  acts like some "VehicleState.build" constructor. but, this also allows the Dispatcher to overwrite
#  multiple instructions for the same vehicle many times in a time step without incurring much cost, since
#  construction of an Instruction is very low cost.
#  anyhow, after finishing all these instructions, there are some things to modify in the Vehicle class,
#  like pointing to the new VehicleState class, removing some methods and attributes. after that, let's see
#  what we broke. :-D


class ChargeStationInstruction(NamedTuple, Instruction):
    vehicle_id: VehicleId
    station_id: StationId
    charger: Charger

    def apply_instruction(self, sim_state: SimulationState) -> Optional[SimulationState]:
        if self.vehicle_id not in sim_state.vehicles:
            log.warning(f"vehicle {self.vehicle_id} not found in simulation ")
            return None
        vehicle = sim_state.vehicles[self.vehicle_id]
        if self.station_id not in sim_state.stations:
            log.warning(f"station {self.station_id} not found in simulation ")
            return None
        station = sim_state.stations[self.station_id]
        if not station.has_available_charger(self.charger):
            log.debug(f"vehicle {self.vehicle_id} can't charge at station {self.station_id}. no plugs available")
            return None

        if not vehicle.can_transition(VehicleState.CHARGING):
            log.debug(f'vehicle {self.vehicle_id} cannot transition to CHARGING')
            return None
        updated_vehicle = vehicle.transition(VehicleState.CHARGING).set_charge_intent(self.charger)

        at_location = sim_state.at_geoid(updated_vehicle.geoid)
        if not at_location['station']:
            log.debug(f"vehicle {self.vehicle_id} not at station {self.station_id}")
            return None

        station_less_charger = station.checkout_charger(self.charger)
        updated_sim_state = sim_state.modify_station(station_less_charger).modify_vehicle(updated_vehicle)

        return updated_sim_state


class ChargeBaseInstruction(NamedTuple, Instruction):
    vehicle_id: VehicleId
    station_id: StationId
    charger: Charger

    def apply_instruction(self, sim_state: SimulationState) -> Optional[SimulationState]:
        if self.vehicle_id not in sim_state.vehicles:
            log.warning(f"vehicle {self.vehicle_id} not found in simulation ")
            return None
        vehicle = sim_state.vehicles[self.vehicle_id]
        if self.station_id not in sim_state.stations:
            log.warning(f"station {self.station_id} not found in simulation ")
            return None
        station = sim_state.stations[self.station_id]
        if not station.has_available_charger(self.charger):
            log.debug(f"vehicle {self.vehicle_id} can't charge at station {self.station_id}. no plugs available")
            return None

        if not vehicle.can_transition(VehicleState.CHARGING):
            log.debug(f'vehicle {self.vehicle_id} cannot transition to CHARGING')
            return None
        updated_vehicle = vehicle.set_charge_intent(self.charger).transition(VehicleState.CHARGING)

        at_location = sim_state.at_geoid(updated_vehicle.geoid)
        if not at_location['station']:
            log.debug(f"vehicle {self.vehicle_id} not at station {self.station_id}")
            return None

        station_less_charger = station.checkout_charger(self.charger)
        updated_sim_state = sim_state.modify_station(station_less_charger).modify_vehicle(updated_vehicle)

        return updated_sim_state


class DispatchBaseInstruction(NamedTuple, Instruction):
    vehicle_id: VehicleId
    destination: GeoId

    def apply_instruction(self, sim_state: SimulationState) -> Optional[SimulationState]:
        if self.vehicle_id not in sim_state.vehicles:
            log.warning(f"vehicle {self.vehicle_id} not found in simulation ")
            return None
        vehicle = sim_state.vehicles[self.vehicle_id]

        if not vehicle.can_transition(VehicleState.DISPATCH_BASE):
            log.debug(f'vehicle {self.vehicle_id} cannot transition to DISPATCH_BASE')
            return None

        if vehicle.vehicle_state in CHARGE_STATES:
            sim_state = _return_charger_patch(sim_state, vehicle.id)
            if not sim_state:
                return None

        vehicle = vehicle.transition(VehicleState.DISPATCH_BASE)

        start = vehicle.geoid
        end = self.destination
        route = sim_state.road_network.route(start, end)

        vehicle_w_route = vehicle.assign_route(route)

        updated_sim_state = sim_state.modify_vehicle(vehicle_w_route)

        return updated_sim_state


class RepositionInstruction(NamedTuple, Instruction):
    vehicle_id: VehicleId
    destination: GeoId

    def apply_instruction(self, sim_state: SimulationState) -> Optional[SimulationState]:
        if self.vehicle_id not in sim_state.vehicles:
            log.warning(f"vehicle {self.vehicle_id} not found in simulation ")
            return None
        vehicle = sim_state.vehicles[self.vehicle_id]

        if not vehicle.can_transition(VehicleState.REPOSITIONING):
            log.debug(f'vehicle {self.vehicle_id} cannot transition to REPOSITIONING')
            return None

        if vehicle.vehicle_state in CHARGE_STATES:
            sim_state = _return_charger_patch(sim_state, vehicle.id)
            if not sim_state:
                return None

        vehicle = vehicle.transition(VehicleState.REPOSITIONING)

        start = vehicle.geoid
        end = self.destination
        route = sim_state.road_network.route(start, end)

        vehicle_w_route = vehicle.assign_route(route)

        updated_sim_state = sim_state.modify_vehicle(vehicle_w_route)

        return updated_sim_state


class ReserveBaseInstruction(NamedTuple, Instruction):
    vehicle_id: VehicleId

    def apply_instruction(self, sim_state: SimulationState) -> Optional[SimulationState]:
        if self.vehicle_id not in sim_state.vehicles:
            log.warning(f"vehicle {self.vehicle_id} not found in simulation ")
            return None
        vehicle = sim_state.vehicles[self.vehicle_id]

        at_location = sim_state.at_geoid(vehicle.geoid)
        if not at_location['base']:
            log.debug(f"vehicle {self.vehicle_id} not at base")
            return None

        if not vehicle.can_transition(VehicleState.RESERVE_BASE):
            log.debug(f'vehicle {self.vehicle_id} cannot transition to RESERVE_BASE')
            return None

        if vehicle.vehicle_state in CHARGE_STATES:
            sim_state = _return_charger_patch(sim_state, vehicle.id)
            if not sim_state:
                return None

        vehicle = vehicle.transition(VehicleState.RESERVE_BASE)
        updated_sim_state = sim_state.modify_vehicle(vehicle)

        return updated_sim_state
