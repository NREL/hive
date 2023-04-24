from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING, Tuple

from nrel.hive.dispatcher.instruction.instruction import Instruction
from nrel.hive.dispatcher.instruction.instruction_ops import (
    trip_plan_ordering_is_valid,
    trip_plan_all_requests_allow_pooling,
    trip_plan_covers_previous,
)
from nrel.hive.dispatcher.instruction.instruction_result import InstructionResult
from nrel.hive.model.entity_position import EntityPosition
from nrel.hive.model.vehicle.trip_phase import TripPhase
from nrel.hive.state.vehicle_state import dispatch_ops
from nrel.hive.state.vehicle_state.charging_base import ChargingBase
from nrel.hive.state.vehicle_state.charging_station import ChargingStation
from nrel.hive.state.vehicle_state.dispatch_base import DispatchBase
from nrel.hive.state.vehicle_state.dispatch_station import DispatchStation
from nrel.hive.state.vehicle_state.dispatch_trip import DispatchTrip
from nrel.hive.state.vehicle_state.idle import Idle
from nrel.hive.state.vehicle_state.repositioning import Repositioning
from nrel.hive.state.vehicle_state.reserve_base import ReserveBase
from nrel.hive.state.vehicle_state.servicing_pooling_trip import ServicingPoolingTrip
from nrel.hive.util.exception import SimulationStateError, InstructionError

log = logging.getLogger(__name__)

if TYPE_CHECKING:
    from nrel.hive.state.simulation_state.simulation_state import SimulationState
    from nrel.hive.util.typealiases import (
        StationId,
        VehicleId,
        RequestId,
        BaseId,
        ChargerId,
        LinkId,
    )
    from nrel.hive.runner.environment import Environment


@dataclass(frozen=True)
class IdleInstruction(Instruction):
    vehicle_id: VehicleId

    def apply_instruction(
        self, sim_state: SimulationState, env: Environment
    ) -> Tuple[Optional[Exception], Optional[InstructionResult]]:
        vehicle = sim_state.vehicles.get(self.vehicle_id)
        if not vehicle:
            return (
                SimulationStateError(
                    f"vehicle {vehicle} not found; context: applying idle instruction."
                ),
                None,
            )
        else:
            prev_state = vehicle.vehicle_state
            next_state = Idle.build(self.vehicle_id)
            return None, InstructionResult(prev_state, next_state)


@dataclass(frozen=True)
class DispatchTripInstruction(Instruction):
    vehicle_id: VehicleId
    request_id: RequestId

    def apply_instruction(
        self, sim_state: SimulationState, env: Environment
    ) -> Tuple[Optional[Exception], Optional[InstructionResult]]:
        vehicle = sim_state.vehicles.get(self.vehicle_id)
        request = sim_state.requests.get(self.request_id)
        if not vehicle:
            return (
                SimulationStateError(
                    f"vehicle {vehicle} not found; context: applying dispatch trip instruction for request {self.request_id}"
                ),
                None,
            )
        elif not request:
            return (
                SimulationStateError(
                    f"request {request} not found; context: applying dispatch trip instruction for vehicle {self.vehicle_id}"
                ),
                None,
            )
        else:
            start = vehicle.position
            end = request.position
            route = sim_state.road_network.route(start, end)
            prev_state = vehicle.vehicle_state
            next_state = DispatchTrip.build(self.vehicle_id, self.request_id, route)

            return None, InstructionResult(prev_state, next_state)


@dataclass(frozen=True)
class DispatchPoolingTripInstruction(Instruction):
    vehicle_id: VehicleId
    trip_plan: Tuple[Tuple[RequestId, TripPhase], ...]

    def apply_instruction(
        self, sim_state: SimulationState, env: Environment
    ) -> Tuple[Optional[Exception], Optional[InstructionResult]]:
        # see https://github.com/NREL/hive/issues/9 for implementation plan
        vehicle = sim_state.vehicles.get(self.vehicle_id)
        if vehicle is None:
            veh_error_msg = f"Vehicle {self.vehicle_id} not found in simulation"
            return SimulationStateError(veh_error_msg), None

        v_state = vehicle.vehicle_state
        if not isinstance(v_state, ServicingPoolingTrip):
            msg = (
                "DispatchPoolingTripInstruction can only be applied to ServicingPoolingTrip states"
            )
            error = InstructionError(msg)
            return error, None

        req_allow_pooling_error_msg = trip_plan_all_requests_allow_pooling(
            sim_state, self.trip_plan
        )
        # seating_error = check_if_vehicle_has_seats(sim_state, vehicle, self.trip_plan)

        if not trip_plan_covers_previous(v_state, self.trip_plan):
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
        # todo: check if the vehicle has the seats available
        #  - this is complicated; we need to walk through the trip plan and add/remove person counts
        #    for each TripPhase, making sure we never exceed the max seats of the vehicle
        #  - if the previous vehicle state is a ServicingPoolingTrip, we need to account for the trip plan
        #    there too
        # elif seating_error is not None:
        #     msg = f"pooling trip plan for vehicle {self.vehicle_id} exceeds seating constraint at step {seating_error}"
        #     error = InstructionError(msg)
        #     return error, None
        elif req_allow_pooling_error_msg is not None:
            msg = f"errors with requests assigned to pooling trip for vehicle {self.vehicle_id}: {req_allow_pooling_error_msg}"
            error = InstructionError(msg)
            return error, None
        else:
            result = dispatch_ops.begin_or_replan_dispatch_pooling_state(
                sim_state, self.vehicle_id, self.trip_plan
            )
            disp_error, next_state = result
            if disp_error is not None:
                return disp_error, None
            elif next_state is None:
                return Exception("Next state should not be none"), None
            else:
                return None, InstructionResult(vehicle.vehicle_state, next_state)


@dataclass(frozen=True)
class DispatchStationInstruction(Instruction):
    vehicle_id: VehicleId
    station_id: StationId
    charger_id: ChargerId

    def apply_instruction(
        self, sim_state: SimulationState, env: Environment
    ) -> Tuple[Optional[Exception], Optional[InstructionResult]]:
        vehicle = sim_state.vehicles.get(self.vehicle_id)
        station = sim_state.stations.get(self.station_id)
        if not vehicle:
            return (
                SimulationStateError(
                    f"vehicle {vehicle} not found: context: applying dispatch station instruction to station {self.station_id}"
                ),
                None,
            )
        elif not station:
            return (
                SimulationStateError(
                    f"station {station} not found: context: applying dispatch station instruction for vehicle {self.vehicle_id}"
                ),
                None,
            )
        else:
            start = vehicle.position
            end = station.position
            route = sim_state.road_network.route(start, end)

            prev_state = vehicle.vehicle_state
            next_state = DispatchStation.build(
                self.vehicle_id, self.station_id, route, self.charger_id
            )

            return None, InstructionResult(prev_state, next_state)


@dataclass(frozen=True)
class ChargeStationInstruction(Instruction):
    vehicle_id: VehicleId
    station_id: StationId
    charger_id: ChargerId

    def apply_instruction(
        self, sim_state: SimulationState, env: Environment
    ) -> Tuple[Optional[Exception], Optional[InstructionResult]]:
        vehicle = sim_state.vehicles.get(self.vehicle_id)
        if not vehicle:
            return (
                SimulationStateError(
                    f"vehicle {vehicle} not found: context: applying charge station instruction at {self.station_id} with {self.charger_id} charger"
                ),
                None,
            )
        else:
            prev_state = vehicle.vehicle_state
            next_state = ChargingStation.build(self.vehicle_id, self.station_id, self.charger_id)

            return None, InstructionResult(prev_state, next_state)


@dataclass(frozen=True)
class ChargeBaseInstruction(Instruction):
    vehicle_id: VehicleId
    base_id: BaseId
    charger_id: ChargerId

    def apply_instruction(
        self, sim_state: SimulationState, env: Environment
    ) -> Tuple[Optional[Exception], Optional[InstructionResult]]:
        vehicle = sim_state.vehicles.get(self.vehicle_id)
        if not vehicle:
            return (
                SimulationStateError(
                    f"vehicle {vehicle} not found; context: applying charge base instruction at base {self.base_id} with {self.charger_id} charger"
                ),
                None,
            )
        else:
            prev_state = vehicle.vehicle_state
            next_state = ChargingBase.build(self.vehicle_id, self.base_id, self.charger_id)

            return None, InstructionResult(prev_state, next_state)


@dataclass(frozen=True)
class DispatchBaseInstruction(Instruction):
    vehicle_id: VehicleId
    base_id: BaseId

    def apply_instruction(
        self, sim_state: SimulationState, env: Environment
    ) -> Tuple[Optional[Exception], Optional[InstructionResult]]:
        vehicle = sim_state.vehicles.get(self.vehicle_id)
        base = sim_state.bases.get(self.base_id)
        if not vehicle:
            return (
                SimulationStateError(
                    f"vehicle {self.vehicle_id} not found; context: applying dispatch base instruction to {self.base_id}"
                ),
                None,
            )
        if not base:
            return (
                SimulationStateError(
                    f"base {self.base_id} not found; context: applying dispatch base instruction for {self.vehicle_id}"
                ),
                None,
            )
        else:
            start = vehicle.position
            end = base.position
            route = sim_state.road_network.route(start, end)

            prev_state = vehicle.vehicle_state
            next_state = DispatchBase.build(self.vehicle_id, self.base_id, route)

            return None, InstructionResult(prev_state, next_state)


@dataclass(frozen=True)
class RepositionInstruction(Instruction):
    vehicle_id: VehicleId
    destination: LinkId

    def apply_instruction(
        self, sim_state: SimulationState, env: Environment
    ) -> Tuple[Optional[Exception], Optional[InstructionResult]]:
        vehicle = sim_state.vehicles.get(self.vehicle_id)
        if not vehicle:
            return (
                SimulationStateError(
                    f"vehicle {self.vehicle_id} not found; context: applying reposition instruction to link {self.destination}"
                ),
                None,
            )
        else:
            start = vehicle.position

            link = sim_state.road_network.link_from_link_id(self.destination)
            if not link:
                return (
                    SimulationStateError(
                        f"link {self.destination} not found; context: applying reposition instruction for vehicle {self.vehicle_id}"
                    ),
                    None,
                )
            else:
                destination_position = EntityPosition(link.link_id, link.end)
                route = sim_state.road_network.route(start, destination_position)

                prev_state = vehicle.vehicle_state
                next_state = Repositioning.build(self.vehicle_id, route)

                return None, InstructionResult(prev_state, next_state)


@dataclass(frozen=True)
class ReserveBaseInstruction(Instruction):
    vehicle_id: VehicleId
    base_id: BaseId

    def apply_instruction(
        self, sim_state: SimulationState, env: Environment
    ) -> Tuple[Optional[Exception], Optional[InstructionResult]]:
        vehicle = sim_state.vehicles.get(self.vehicle_id)
        if not vehicle:
            return (
                SimulationStateError(
                    f"vehicle {self.vehicle_id} not found; context: applying reserve base instruction at base {self.base_id}"
                ),
                None,
            )

        prev_state = vehicle.vehicle_state
        next_state = ReserveBase.build(self.vehicle_id, self.base_id)

        return None, InstructionResult(prev_state, next_state)
