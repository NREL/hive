from __future__ import annotations

import logging
from typing import NamedTuple, Tuple, TYPE_CHECKING, Optional

import immutables

from hive.model.request import Request
from hive.model.roadnetwork import Route
from hive.model.sim_time import SimTime
from hive.model.vehicle.trip_phase import TripPhase
from hive.runner.environment import Environment
from hive.state.vehicle_state.idle import Idle
from hive.state.vehicle_state.out_of_service import OutOfService
from hive.state.vehicle_state.servicing_ops import get_active_pooling_trip, pick_up_trip, \
    update_active_pooling_trip, transitioning_from_dispatch_trip
from hive.state.vehicle_state.vehicle_state import VehicleState
from hive.state.vehicle_state.vehicle_state_ops import move
from hive.util import SimulationStateError, TupleOps
from hive.util.typealiases import RequestId, VehicleId

if TYPE_CHECKING:
    from hive.state.simulation_state.simulation_state import SimulationState

log = logging.getLogger(__name__)


class ServicingPoolingTrip(NamedTuple, VehicleState):
    """
    a pooling trip is in service, for the given trips in the given trip_order.
    """
    vehicle_id: VehicleId
    trip_plan: Tuple[Tuple[RequestId, TripPhase], ...]
    boarded_requests: immutables.Map[RequestId, Request]
    departure_times: immutables.Map[RequestId, SimTime]
    routes: Tuple[Route, ...]
    num_passengers: int

    def update(self, sim: SimulationState, env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        return VehicleState.default_update(sim, env, self)

    def enter(self, sim: SimulationState, env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        """
        transition from DispatchTrip into a pooling trip service leg

        :param sim: the simulation state
        :param env: the simulation environment
        :return: an error, or, the sim with state entered
        """
        # validate the first step of the trip plan for this vehicle
        vehicle = sim.vehicles.get(self.vehicle_id)
        first_trip_phase = TupleOps.head_optional(self.trip_plan)

        if vehicle is None:
            return SimulationStateError(f"vehicle {self.vehicle_id} not found"), None
        elif not transitioning_from_dispatch_trip(vehicle):
            # the only supported transition into ServicingPoolingTrip comes from DispatchTrip
            prev_state = vehicle.vehicle_state.__class__.__name__
            msg = f"ServicingTrip called for vehicle {vehicle.id} but previous state ({prev_state}) is not DispatchTrip as required"
            error = SimulationStateError(msg)
            return error, None
        elif first_trip_phase is None:
            msg = f"vehicle {self.vehicle_id} attempting to enter a ServicingPoolingTrip state without any trip plan"
            error = SimulationStateError(msg)
            return error, None
        else:

            # validate the request for the first step in the trip plan
            request_id, trip_phase = first_trip_phase
            request = sim.requests.get(request_id)

            if trip_phase is not TripPhase.PICKUP:
                msg = f"vehicle {vehicle.id} attempting to enter ServicingPoolingTrip but first request in plan {request_id} expects a DROPOFF phase which is irrational"
                return SimulationStateError(msg), None
            elif request is None:
                msg = f"vehicle {vehicle.id} has ServicingPoolingTrip with request {request_id} stored in trip plan but not in requests collection"
                return SimulationStateError(msg), None
            elif not request.membership.grant_access_to_membership(vehicle.membership):
                msg = f"vehicle {vehicle.id} attempting to service request {self.request.id} with mis-matched memberships/fleets"
                return SimulationStateError(msg), None
            else:

                # perform pickup action, removing request from the simulation
                pickup_error, pickup_sim = pick_up_trip(sim, env, self.vehicle_id, request_id)
                if pickup_error:
                    return pickup_error, None
                else:
                    boarded_state = self._replace(boarded_requests=immutables.Map({request.id: request}))
                    enter_result = VehicleState.apply_new_vehicle_state(pickup_sim, self.vehicle_id, boarded_state)
                    return enter_result

    def exit(self, sim: SimulationState, env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        """
        cannot call "exit" on ServicingPoolingTrip, must be exited via it's update method.
        the state is modeling a trip. exiting would mean dropping off passengers prematurely.
        this is only valid when falling OutOfService or when reaching the destination.
        both of these transitions occur during the update step of ServicingPoolingTrip.

        :param sim: the sim state
        :param env: the sim environment
        :return: None, None - cannot invoke "exit" on ServicingPoolingTrip
        """
        # todo: allow transitioning to a DispatchPoolingTrip state
        return None, None

    def _has_reached_terminal_state_condition(self, sim: SimulationState, env: Environment) -> bool:
        """
        ignored: this should be handled in the update phase when the length of the final route is zero.

        :param sim: the simulation state
        :param env: the simulation environment
        :return: true if our trip is done
        """
        return False

    def _enter_default_terminal_state(self,
                                      sim: SimulationState,
                                      env: Environment) -> Tuple[Optional[Exception], Optional[Tuple[SimulationState, VehicleState]]]:
        """
        after dropping off the last passenger, we default to an idle state. this
        behavior is more likely to have occurred during an update.

        :param sim: the simulation state
        :param env: the simulation environment
        :return: this vehicle in an idle state
        """
        next_state = Idle(self.vehicle_id)
        enter_error, enter_sim = next_state.enter(sim, env)
        if enter_error:
            return enter_error, None
        else:
            return None, (enter_sim, next_state)

    def _perform_update(self, sim: SimulationState, env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        """
        move forward on our trip, making pickups and dropoffs as needed

        :param sim: the simulation state
        :param env: the simulation environment
        :return: the vehicle after advancing in time on a servicing trip
        """

        # grab the current trip
        err1, active_trip = get_active_pooling_trip(self)
        if err1 is not None:
            return err1, None
        else:
            # move forward in current trip plan
            move_error, move_result = move(sim, env, self.vehicle_id, active_trip.route)
            moved_vehicle = move_result.sim.vehicles.get(self.vehicle_id) if move_result else None

            if move_error:
                return move_error, None
            elif not moved_vehicle:
                return SimulationStateError(f"vehicle {self.vehicle_id} not found"), None
            elif isinstance(moved_vehicle.vehicle_state, OutOfService):
                return None, move_result.sim
            else:
                # update moved vehicle's state
                updated_route = move_result.route_traversal.remaining_route
                err2, sim2 = update_active_pooling_trip(move_result.sim, env, self, updated_route)
                updated_vehicle = sim2.vehicles.get(self.vehicle_id)
                if updated_vehicle is None:
                    return SimulationStateError(f"vehicle {self.vehicle_id} not found"), None
                elif isinstance(updated_vehicle.vehicle_state, ServicingPoolingTrip):
                    # if we finished all trip plans, we can terminate this ServicingPoolingTrip state
                    if len(updated_vehicle.vehicle_state.trip_plan) == 0:
                        # todo: generate "end of pooling trip" report, calculate all request travel times
                        #  using ServicingPoolingTrip.departure_times
                        idle_result = self._enter_default_terminal_state(sim2, env)
                        return idle_result
                    else:
                        return None, sim2
                else:
                    # somehow our vehicle fell off it's ServicingPoolingTrip horse during this update
                    state_name = updated_vehicle.vehicle_state.__class__.__name__
                    err3 = SimulationStateError(f"vehicle {self.vehicle_id} had invalid state change from ServicingPoolingTrip to {state_name}")
                    return err3, None
