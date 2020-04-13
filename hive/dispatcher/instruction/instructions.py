from __future__ import annotations

import logging
from typing import NamedTuple, Optional, TYPE_CHECKING, Tuple

from hive.dispatcher.instruction.instruction_interface import Instruction
from hive.model.energy.charger import Charger
from hive.model.passenger import board_vehicle
from hive.runner.environment import Environment
from hive.state.entity_state import entity_state_ops
from hive.state.vehicle_state import *
from hive.util.exception import SimulationStateError
from hive.util.typealiases import StationId, VehicleId, RequestId, GeoId, BaseId

log = logging.getLogger(__name__)

if TYPE_CHECKING:
    from hive.state.simulation_state.simulation_state import SimulationState
    from hive.state.vehicle_state import VehicleState


class IdleInstruction(NamedTuple, Instruction):
    vehicle_id: VehicleId

    def apply_instruction(self,
                          sim_state: SimulationState,
                          env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        vehicle = sim_state.vehicles.get(self.vehicle_id)
        if not vehicle:
            return SimulationStateError(f"vehicle {vehicle} not found"), None
        else:
            prev_state = vehicle.vehicle_state
            next_state = Idle(self.vehicle_id)
            return entity_state_ops.transition_previous_to_next(sim_state, env, prev_state, next_state)


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
            return entity_state_ops.transition_previous_to_next(sim_state, env, prev_state, next_state)


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

            passengers = board_vehicle(request.passengers, self.vehicle_id)

            prev_state = vehicle.vehicle_state
            next_state = ServicingTrip(self.vehicle_id, self.request_id, route, passengers)

            VehicleState.apply_new_vehicle_state(sim_state, self.vehicle_id, next_state)
            result = entity_state_ops.transition_previous_to_next(sim_state, env, prev_state, next_state)
            return result


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

            result = entity_state_ops.transition_previous_to_next(sim_state, env, prev_state, next_state)
            return result


class ChargeStationInstruction(NamedTuple, Instruction):
    vehicle_id: VehicleId
    station_id: StationId
    charger: Charger

    def apply_instruction(self,
                          sim_state: SimulationState,
                          env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        vehicle = sim_state.vehicles.get(self.vehicle_id)
        if not vehicle:
            return SimulationStateError(f"vehicle {vehicle} not found"), None
        else:
            prev_state = vehicle.vehicle_state
            next_state = ChargingStation(self.vehicle_id, self.station_id, self.charger)

            result = entity_state_ops.transition_previous_to_next(sim_state, env, prev_state, next_state)
            return result


class ChargeBaseInstruction(NamedTuple, Instruction):
    vehicle_id: VehicleId
    base_id: BaseId
    charger: Charger

    def apply_instruction(self,
                          sim_state: SimulationState,
                          env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        vehicle = sim_state.vehicles.get(self.vehicle_id)
        if not vehicle:
            return SimulationStateError(f"vehicle {vehicle} not found"), None
        else:
            prev_state = vehicle.vehicle_state
            next_state = ChargingBase(self.vehicle_id, self.base_id, self.charger)

            result = entity_state_ops.transition_previous_to_next(sim_state, env, prev_state, next_state)
            return result


class DispatchBaseInstruction(NamedTuple, Instruction):
    vehicle_id: VehicleId
    base_id: BaseId

    def apply_instruction(self,
                          sim_state: SimulationState,
                          env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        vehicle = sim_state.vehicles.get(self.vehicle_id)
        base = sim_state.bases.get(self.base_id)
        if not vehicle:
            return SimulationStateError(f"vehicle {self.vehicle_id} not found"), None
        if not base:
            return SimulationStateError(f"base {self.base_id} not found"), None
        else:
            start = vehicle.geoid
            end = base.geoid
            route = sim_state.road_network.route(start, end)

            prev_state = vehicle.vehicle_state
            next_state = DispatchBase(self.vehicle_id, self.base_id, route)

            result = entity_state_ops.transition_previous_to_next(sim_state, env, prev_state, next_state)
            return result


class RepositionInstruction(NamedTuple, Instruction):
    vehicle_id: VehicleId
    destination: GeoId

    def apply_instruction(self,
                          sim_state: SimulationState,
                          env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        vehicle = sim_state.vehicles.get(self.vehicle_id)
        if not vehicle:
            return SimulationStateError(f"vehicle {self.vehicle_id} not found"), None
        else:
            start = vehicle.geoid
            route = sim_state.road_network.route(start, self.destination)

            prev_state = vehicle.vehicle_state
            next_state = Repositioning(self.vehicle_id, route)

            result = entity_state_ops.transition_previous_to_next(sim_state, env, prev_state, next_state)
            return result


class ReserveBaseInstruction(NamedTuple, Instruction):
    vehicle_id: VehicleId
    base_id: BaseId

    def apply_instruction(self,
                          sim_state: SimulationState,
                          env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        vehicle = sim_state.vehicles.get(self.vehicle_id)
        if not vehicle:
            return SimulationStateError(f"vehicle {self.vehicle_id} not found"), None

        prev_state = vehicle.vehicle_state
        next_state = ReserveBase(self.vehicle_id, self.base_id)

        result = entity_state_ops.transition_previous_to_next(sim_state, env, prev_state, next_state)
        return result
