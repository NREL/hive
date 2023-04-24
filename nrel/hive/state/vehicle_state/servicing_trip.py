from __future__ import annotations

import logging
from dataclasses import dataclass, replace
from typing import Tuple, Optional, TYPE_CHECKING
from uuid import uuid4

from nrel.hive.model.request import Request
from nrel.hive.model.roadnetwork.route import (
    Route,
    route_cooresponds_with_entities,
)
from nrel.hive.model.sim_time import SimTime
from nrel.hive.runner.environment import Environment
from nrel.hive.state.vehicle_state.idle import Idle
from nrel.hive.state.vehicle_state.servicing_ops import (
    drop_off_trip,
    pick_up_trip,
)
from nrel.hive.state.vehicle_state.vehicle_state import (
    VehicleState,
    VehicleStateInstanceId,
)
from nrel.hive.state.vehicle_state.vehicle_state_ops import move
from nrel.hive.state.vehicle_state.vehicle_state_type import VehicleStateType
from nrel.hive.util.exception import SimulationStateError
from nrel.hive.util.typealiases import VehicleId

if TYPE_CHECKING:
    from nrel.hive.state.simulation_state.simulation_state import SimulationState

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class ServicingTrip(VehicleState):
    vehicle_id: VehicleId
    request: Request
    departure_time: SimTime
    route: Route

    instance_id: VehicleStateInstanceId

    @classmethod
    def build(
        cls,
        vehicle_id: VehicleId,
        request: Request,
        departure_time: SimTime,
        route: Route,
    ) -> ServicingTrip:
        """
        build a servicing trip state

        :param vehicle_id: the vehicle id
        :param request: the request
        :param departure_time: the departure time
        :param route: the route
        :return: the servicing trip state
        """
        return cls(
            vehicle_id=vehicle_id,
            request=request,
            departure_time=departure_time,
            route=route,
            instance_id=uuid4(),
        )

    @property
    def vehicle_state_type(cls) -> VehicleStateType:
        return VehicleStateType.SERVICING_TRIP

    def update_route(self, route: Route) -> ServicingTrip:
        return replace(self, route=route)

    def update(
        self, sim: SimulationState, env: Environment
    ) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        return VehicleState.default_update(sim, env, self)

    def enter(
        self, sim: SimulationState, env: Environment
    ) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        """
        transition from DispatchTrip into a non-pooling trip service leg

        :param sim: the simulation state
        :param env: the simulation environment
        :return: an error, or, the sim with state entered
        """

        vehicle = sim.vehicles.get(self.vehicle_id)
        request = sim.requests.get(self.request.id)
        is_valid = (
            route_cooresponds_with_entities(
                self.route,
                request.position,
                request.destination_position,
            )
            if vehicle and request
            else False
        )
        context = (
            f"vehicle {self.vehicle_id} entering servicing trip state for request {self.request.id}"
        )
        if vehicle is None:
            return (
                SimulationStateError(f"vehicle not found; context: {context}"),
                None,
            )
        elif request is None:
            # request moved on to greener pastures
            return None, None
        elif not is_valid:
            msg = "ServicingTrip route does not correspond to request"
            return SimulationStateError(msg), None
        elif not vehicle.vehicle_state.vehicle_state_type == VehicleStateType.DISPATCH_TRIP:
            # the only supported transition into ServicingTrip comes from DispatchTrip
            prev_state = vehicle.vehicle_state.__class__.__name__
            msg = f"ServicingTrip called for vehicle {vehicle.id} but previous state ({prev_state}) is not DispatchTrip as required"
            error = SimulationStateError(msg)
            return error, None
        elif not self.request.membership.grant_access_to_membership(vehicle.membership):
            msg = f"vehicle {vehicle.id} attempting to service request {self.request.id} with mis-matched memberships/fleets"
            return SimulationStateError(msg), None
        elif not route_cooresponds_with_entities(self.route, vehicle.position):
            msg = f"vehicle {vehicle.id} attempting to service request {self.request.id} invalid route (doesn't match location of vehicle)"
            log.warning(msg)
            return None, None
        elif not route_cooresponds_with_entities(
            self.route, request.position, request.destination_position
        ):
            msg = f"vehicle {vehicle.id} attempting to service request {self.request.id} invalid route (doesn't match o/d of request)"
            log.warning(msg)
            return None, None
        else:
            pickup_error, pickup_sim = pick_up_trip(sim, env, self.vehicle_id, self.request.id)
            if pickup_error:
                response = SimulationStateError(
                    f"failure during ServicingTrip.enter for vehicle {self.vehicle_id}"
                )
                response.__cause__ = pickup_error
                return response, None
            elif pickup_sim is None:
                return None, None
            else:
                enter_result = VehicleState.apply_new_vehicle_state(
                    pickup_sim, self.vehicle_id, self
                )
                return enter_result

    def exit(
        self, next_state: VehicleState, sim: SimulationState, env: Environment
    ) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        """
        leave this state when the route is completed

        :param sim: the sim state
        :param env: the sim environment
        :return: None, None - cannot invoke "exit" on ServicingTrip
        """
        if len(self.route) == 0:
            return None, sim
        else:
            return None, None

    def _has_reached_terminal_state_condition(self, sim: SimulationState, env: Environment) -> bool:
        """
        if the route is complete we are finished

        :param sim: the sim state
        :param env: the sim environment
        :return: True if we have reached the base
        """
        return len(self.route) == 0

    def _default_terminal_state(
        self, sim: SimulationState, env: Environment
    ) -> Tuple[Optional[Exception], Optional[VehicleState]]:
        """
        gets the default terminal state for this state which should be transitioned to
        once it reaches the end of the current task.
        :param sim: the sim state
        :param env: the sim environment
        :return: an exception or the default VehicleState
        """
        next_state = Idle.build(self.vehicle_id)
        return None, next_state

    def _perform_update(
        self, sim: SimulationState, env: Environment
    ) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        """
        take a step along the route to a trip destination

        :param sim: the simulation state
        :param env: the simulation environment
        :return: the sim state with vehicle moved
        """
        context = f"vehicle {self.vehicle_id} serving trip for request {self.request.id}"

        move_error, move_sim = move(sim, env, self.vehicle_id)

        if move_error:
            response = SimulationStateError(
                f"failure during ServicingTrip._perform_update for vehicle {self.vehicle_id}"
            )
            response.__cause__ = move_error
            return response, None
        elif move_sim is None:
            return None, None

        moved_vehicle = move_sim.vehicles.get(self.vehicle_id)

        if not moved_vehicle:
            return (
                SimulationStateError(f"vehicle not found; context: {context}"),
                None,
            )
        elif moved_vehicle.vehicle_state.vehicle_state_type == VehicleStateType.OUT_OF_SERVICE:
            return None, move_sim

        if isinstance(moved_vehicle.vehicle_state, ServicingTrip):
            if len(moved_vehicle.vehicle_state.route) == 0:
                # reached destination.
                # let's drop the passengers off during this time step
                result = drop_off_trip(move_sim, env, self.vehicle_id, self.request)
                return result
            else:
                return None, move_sim
        else:
            return None, move_sim
