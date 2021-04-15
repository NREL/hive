from __future__ import annotations

import logging
from typing import NamedTuple, Optional, TYPE_CHECKING, Tuple

from hive.dispatcher.instruction.instruction import Instruction
from hive.dispatcher.instruction.instruction_ops import create_reroute_pooling_trip, trip_plan_ordering_is_valid, trip_plan_covers_previous, \
    trip_plan_all_requests_allow_pooling, create_dispatch_pooling_trip, test_vehicle_has_seats
from hive.dispatcher.instruction.instruction_result import InstructionResult
from hive.model.roadnetwork.link import Link
from hive.model.vehicle.trip_phase import TripPhase
from hive.state.vehicle_state.charging_base import ChargingBase
from hive.state.vehicle_state.charging_station import ChargingStation
from hive.state.vehicle_state.dispatch_base import DispatchBase
from hive.state.vehicle_state.dispatch_station import DispatchStation
from hive.state.vehicle_state.dispatch_trip import DispatchTrip
from hive.state.vehicle_state.idle import Idle
from hive.state.vehicle_state.repositioning import Repositioning
from hive.state.vehicle_state.reserve_base import ReserveBase
from hive.state.vehicle_state.servicing_pooling_trip import ServicingPoolingTrip
from hive.state.vehicle_state.servicing_pooling_trip import ServicingPoolingTrip
from hive.util.exception import SimulationStateError, InstructionError

log = logging.getLogger(__name__)

if TYPE_CHECKING:
    from hive.state.simulation_state.simulation_state import SimulationState
    from hive.util.typealiases import StationId, VehicleId, RequestId, BaseId, ChargerId
    from hive.runner.environment import Environment


class IdleInstruction(NamedTuple, Instruction):
    vehicle_id: VehicleId

    def apply_instruction(self,
                          sim_state: SimulationState,
                          env: Environment) -> Tuple[Optional[Exception], Optional[InstructionResult]]:
        vehicle = sim_state.vehicles.get(self.vehicle_id)
        if not vehicle:
            return SimulationStateError(f"vehicle {vehicle} not found"), None
        else:
            prev_state = vehicle.vehicle_state
            next_state = Idle(self.vehicle_id)
            return None, InstructionResult(prev_state, next_state)


class DispatchTripInstruction(NamedTuple, Instruction):
    vehicle_id: VehicleId
    request_id: RequestId

    def apply_instruction(self,
                          sim_state: SimulationState,
                          env: Environment) -> Tuple[Optional[Exception], Optional[InstructionResult]]:
        vehicle = sim_state.vehicles.get(self.vehicle_id)
        request = sim_state.requests.get(self.request_id)
        if not vehicle:
            return SimulationStateError(f"vehicle {vehicle} not found"), None
        elif not request:
            return SimulationStateError(f"request {request} not found"), None
        else:
            start = vehicle.link
            end = request.origin_link
            route = sim_state.road_network.route(start, end)
            prev_state = vehicle.vehicle_state
            next_state = DispatchTrip(self.vehicle_id, self.request_id, route)

            return None, InstructionResult(prev_state, next_state)


class DispatchPoolingTripInstruction(NamedTuple, Instruction):
    vehicle_id: VehicleId
    trip_plan: Tuple[Tuple[RequestId, TripPhase], ...]

    def apply_instruction(self, sim_state: SimulationState, env: Environment) -> Tuple[Optional[Exception], Optional[InstructionResult]]:
        # see https://github.com/NREL/hive/issues/9 for implementation plan
        vehicle = sim_state.vehicles.get(self.vehicle_id)
        v_state = vehicle.vehicle_state

        req_allow_pooling_error_msg = trip_plan_all_requests_allow_pooling(sim_state, self.trip_plan)
        seating_error = test_vehicle_has_seats(sim_state, vehicle, self.trip_plan)

        if isinstance(v_state, ServicingPoolingTrip) and not trip_plan_covers_previous(v_state, self.trip_plan):
            msg = "DispatchPoolingTripInstruction updates an active pooling state but doesn't include all previous requests"
            error = InstructionError(msg)
            return error, None
        elif not trip_plan_ordering_is_valid(self.trip_plan, v_state):
            msg = f"DispatchPoolingTripInstruction trip order is unsound :{self.trip_plan}"
            error = InstructionError(msg)
            return error, None
        elif not vehicle.driver_state.allows_pooling:
            msg = f"attempting to assign a pooling trip to vehicle {self.vehicle_id} which does not allow pooling"
            error = InstructionError(msg)
            return error, None
        elif seating_error is not None:
            msg = f"pooling trip plan for vehicle {self.vehicle_id} exceeds seating constraint at step {seating_error}"
            error = InstructionError(msg)
            return error, None
        elif req_allow_pooling_error_msg is not None:
            msg = f"errors with requests assigned to pooling trip for vehicle {self.vehicle_id}: {req_allow_pooling_error_msg}"
            error = InstructionError(msg)
            return error, None
        else:
            # todo: do we want a DispatchPoolingTrip state, which tracks the longer-term plan we devised here?
            #  - DispatchPoolingTrip would get us to the first trip plan step and then convert us into ServicingPoolingTrip
            #  - using only DispatchTrip here instead would mean our DispatchTrip should also allow an optional trip_plan to pass along
            pass
            # error, next_state = create_dispatch_pooling_trip(sim_state, vehicle, self.trip_plan)
            # if error is not None:
            #     return error, None
            # else:
            #     return None, InstructionResult(vehicle.vehicle_state, next_state)


# class ReroutePoolingTripInstruction(NamedTuple, Instruction):
#     vehicle_id: VehicleId
#     trip_order: Tuple[RequestId, ...]
#
#     def apply_instruction(self,
#                           sim_state: SimulationState,
#                           env: Environment) -> Tuple[Optional[Exception], Optional[InstructionResult]]:
#
#         vehicle = sim_state.vehicles.get(self.vehicle_id)
#         new_trip_request_ids = set(self.trip_order).difference(vehicle.vehicle_state.trip_order) if vehicle else None
#         new_trip_requests = tuple(map(sim_state.requests.get, new_trip_request_ids)) if new_trip_request_ids else None
#
#         if not vehicle:
#             return SimulationStateError(f"vehicle {self.vehicle_id} not found"), None
#         elif not isinstance(vehicle.vehicle_state, ServicingPoolingTrip):
#             return SimulationStateError(f"vehicle {self.vehicle_id} not pooling but instructed to re-route for pooling"), None
#         elif any(map(lambda r: r is None, new_trip_requests)):
#             r_ids, _ = zip(*(filter(lambda pair: pair[1] is None, zip(self.trip_order, new_trip_requests))))
#             return SimulationStateError(f"requests {r_ids} for pooling trip not found"), None
#         else:
#             # make sure the user included all request ids, including ones that may be mid-flight
#             old_reqs_missing = set(vehicle.vehicle_state.trip_order).difference(self.trip_order) if vehicle else None
#             if len(old_reqs_missing) > 0:
#                 return SimulationStateError(f"new re-route plan is missing current request ids {old_reqs_missing}"), None
#             else:
#                 # create the rerouting state, computing all new routes in the supplied order
#                 prev_state = vehicle.vehicle_state
#                 error, next_state = create_reroute_pooling_trip(sim_state, env, vehicle, self.trip_order, new_trip_requests)
#                 if error:
#                     return error, None
#                 else:
#                     return None, InstructionResult(prev_state, next_state)


class DispatchStationInstruction(NamedTuple, Instruction):
    vehicle_id: VehicleId
    station_id: StationId
    charger_id: ChargerId

    def apply_instruction(self,
                          sim_state: SimulationState,
                          env: Environment) -> Tuple[Optional[Exception], Optional[InstructionResult]]:
        vehicle = sim_state.vehicles.get(self.vehicle_id)
        station = sim_state.stations.get(self.station_id)
        if not vehicle:
            return SimulationStateError(f"vehicle {vehicle} not found"), None
        elif not station:
            return SimulationStateError(f"station {station} not found"), None
        else:
            start = vehicle.link
            end = station.link
            route = sim_state.road_network.route(start, end)

            prev_state = vehicle.vehicle_state
            next_state = DispatchStation(self.vehicle_id, self.station_id, route, self.charger_id)

            return None, InstructionResult(prev_state, next_state)


class ChargeStationInstruction(NamedTuple, Instruction):
    vehicle_id: VehicleId
    station_id: StationId
    charger_id: ChargerId

    def apply_instruction(self,
                          sim_state: SimulationState,
                          env: Environment) -> Tuple[Optional[Exception], Optional[InstructionResult]]:
        vehicle = sim_state.vehicles.get(self.vehicle_id)
        if not vehicle:
            return SimulationStateError(f"vehicle {vehicle} not found"), None
        else:
            prev_state = vehicle.vehicle_state
            next_state = ChargingStation(self.vehicle_id, self.station_id, self.charger_id)

            return None, InstructionResult(prev_state, next_state)


class ChargeBaseInstruction(NamedTuple, Instruction):
    vehicle_id: VehicleId
    base_id: BaseId
    charger_id: ChargerId

    def apply_instruction(self,
                          sim_state: SimulationState,
                          env: Environment) -> Tuple[Optional[Exception], Optional[InstructionResult]]:
        vehicle = sim_state.vehicles.get(self.vehicle_id)
        if not vehicle:
            return SimulationStateError(f"vehicle {vehicle} not found"), None
        else:
            prev_state = vehicle.vehicle_state
            next_state = ChargingBase(self.vehicle_id, self.base_id, self.charger_id)

            return None, InstructionResult(prev_state, next_state)


class DispatchBaseInstruction(NamedTuple, Instruction):
    vehicle_id: VehicleId
    base_id: BaseId

    def apply_instruction(self,
                          sim_state: SimulationState,
                          env: Environment) -> Tuple[Optional[Exception], Optional[InstructionResult]]:
        vehicle = sim_state.vehicles.get(self.vehicle_id)
        base = sim_state.bases.get(self.base_id)
        if not vehicle:
            return SimulationStateError(f"vehicle {self.vehicle_id} not found"), None
        if not base:
            return SimulationStateError(f"base {self.base_id} not found"), None
        else:
            start = vehicle.link
            end = base.link
            route = sim_state.road_network.route(start, end)

            prev_state = vehicle.vehicle_state
            next_state = DispatchBase(self.vehicle_id, self.base_id, route)

            return None, InstructionResult(prev_state, next_state)


class RepositionInstruction(NamedTuple, Instruction):
    vehicle_id: VehicleId
    destination: Link

    def apply_instruction(self,
                          sim_state: SimulationState,
                          env: Environment) -> Tuple[Optional[Exception], Optional[InstructionResult]]:
        vehicle = sim_state.vehicles.get(self.vehicle_id)
        if not vehicle:
            return SimulationStateError(f"vehicle {self.vehicle_id} not found"), None
        else:
            start = vehicle.link
            route = sim_state.road_network.route(start, self.destination)

            prev_state = vehicle.vehicle_state
            next_state = Repositioning(self.vehicle_id, route)

            return None, InstructionResult(prev_state, next_state)


class ReserveBaseInstruction(NamedTuple, Instruction):
    vehicle_id: VehicleId
    base_id: BaseId

    def apply_instruction(self,
                          sim_state: SimulationState,
                          env: Environment) -> Tuple[Optional[Exception], Optional[InstructionResult]]:
        vehicle = sim_state.vehicles.get(self.vehicle_id)
        if not vehicle:
            return SimulationStateError(f"vehicle {self.vehicle_id} not found"), None

        prev_state = vehicle.vehicle_state
        next_state = ReserveBase(self.vehicle_id, self.base_id)

        return None, InstructionResult(prev_state, next_state)
