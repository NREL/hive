from __future__ import annotations

import logging
from typing import NamedTuple, Tuple, Optional, TYPE_CHECKING

from hive.model.request import Request
from hive.model.roadnetwork.route import Route, route_cooresponds_with_entities
from hive.model.sim_time import SimTime
from hive.runner.environment import Environment
from hive.state.simulation_state import simulation_state_ops
from hive.state.vehicle_state.idle import Idle
from hive.state.vehicle_state.servicing_ops import drop_off_trip, pick_up_trip
from hive.state.vehicle_state.vehicle_state import VehicleState
from hive.state.vehicle_state.vehicle_state_ops import move
from hive.state.vehicle_state.vehicle_state_type import VehicleStateType
from hive.util.exception import SimulationStateError
from hive.util.typealiases import VehicleId

if TYPE_CHECKING:
    from hive.state.simulation_state.simulation_state import SimulationState

log = logging.getLogger(__name__)


class ServicingTrip(NamedTuple, VehicleState):
    vehicle_id: VehicleId
    request: Request
    departure_time: SimTime
    route: Route

    @property
    def vehicle_state_type(cls) -> VehicleStateType:
        return VehicleStateType.SERVICING_TRIP

    def update(self,
               sim: SimulationState,
               env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        return VehicleState.default_update(sim, env, self)

    def enter(self,
              sim: SimulationState,
              env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        """
        transition from DispatchTrip into a non-pooling trip service leg

        :param sim: the simulation state
        :param env: the simulation environment
        :return: an error, or, the sim with state entered
        """
        vehicle = sim.vehicles.get(self.vehicle_id)
        request = sim.requests.get(self.request.id)
        is_valid = route_cooresponds_with_entities(self.route, request.origin_position, request.destination_position) if vehicle and request else False
        context = f"vehicle {self.vehicle_id} entering servicing trip state for request {self.request.id}"
        if vehicle is None:
            return SimulationStateError(f"vehicle not found; context: {context}"), None
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
        elif not route_cooresponds_with_entities(self.route, request.origin_position, request.destination_position):
            msg = f"vehicle {vehicle.id} attempting to service request {self.request.id} invalid route (doesn't match o/d of request)"
            log.warning(msg)
            return None, None
        else:
            pickup_error, pickup_sim = pick_up_trip(sim, env, self.vehicle_id, self.request.id)
            if pickup_error:
                return pickup_error, None
            else:
                enter_result = VehicleState.apply_new_vehicle_state(pickup_sim, self.vehicle_id, self)
                return enter_result

    def exit(self,
             next_state: VehicleState,
             sim: SimulationState,
             env: Environment
             ) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        """
        cannot call "exit" on ServicingTrip, must be exited via it's update method.
        the state is modeling a trip. exiting would mean dropping off passengers prematurely.
        this is only valid when falling OutOfService or when reaching the destination.
        both of these transitions occur during the update step of ServicingTrip.

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
        ignored: this should be handled in the update phase when the length of the route is zero.

        :param sim: the sim state
        :param env: the sim environment
        :return: True if we have reached the base
        """
        return len(self.route) == 0

    def _default_terminal_state(self,
                                sim: SimulationState,
                                env: Environment) -> Tuple[Optional[Exception], Optional[VehicleState]]:
        """
        gets the default terminal state for this state which should be transitioned to
        once it reaches the end of the current task.
        :param sim: the sim state
        :param env: the sim environment
        :return: an exception or the default VehicleState
        """
        next_state = Idle(self.vehicle_id)
        return None, next_state

    def _perform_update(self,
                        sim: SimulationState,
                        env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        """
        take a step along the route to the base

        :param sim: the simulation state
        :param env: the simulation environment
        :return: the sim state with vehicle moved
        """

        move_error, move_result = move(sim, env, self.vehicle_id, self.route)
        moved_vehicle = move_result.sim.vehicles.get(self.vehicle_id) if move_result else None

        context = f"vehicle {self.vehicle_id} serving trip for request {self.request.id}"
        if move_error:
            return move_error, None
        elif not moved_vehicle:
            return SimulationStateError(f"vehicle not found; context: {context}"), None
        elif moved_vehicle.vehicle_state.vehicle_state_type == VehicleStateType.OUT_OF_SERVICE:
            return None, move_result.sim
        else:
            # update moved vehicle's state
            updated_route = move_result.route_traversal.remaining_route
            updated_state = self._replace(route=updated_route)
            updated_vehicle = moved_vehicle.modify_vehicle_state(updated_state)
            error2, sim2 = simulation_state_ops.modify_vehicle(move_result.sim, updated_vehicle)

            if error2:
                return error2, None
            elif len(updated_route) == 0:
                # reached destination.
                # let's drop the passengers off during this time step
                result = drop_off_trip(sim2, env, self.vehicle_id, self.request)
                return result
                # if error3:
                #     return error3, None
                # else:
                #     err, term_result = self._enter_default_terminal_state(sim3, env)
                #     term_sim, _ = term_result
                #     return err, term_sim
            else:
                return None, sim2
