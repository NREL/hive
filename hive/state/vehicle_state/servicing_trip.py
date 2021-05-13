from __future__ import annotations

import logging
from typing import NamedTuple, Tuple, Optional, TYPE_CHECKING

from hive.model.request import Request
from hive.model.roadnetwork import Route
from hive.model.sim_time import SimTime
from hive.runner.environment import Environment
from hive.state.simulation_state import simulation_state_ops
from hive.state.vehicle_state.idle import Idle
from hive.state.vehicle_state.out_of_service import OutOfService
from hive.state.vehicle_state.servicing_ops import drop_off_trip, pick_up_trip
from hive.state.vehicle_state.vehicle_state import VehicleState
from hive.state.vehicle_state.vehicle_state_ops import move
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
        if vehicle is None:
            return SimulationStateError(f"vehicle {self.vehicle_id} not found"), None
        elif not vehicle.vehicle_state.__class__.__name__ == "DispatchTrip":
            # the only supported transition into ServicingTrip comes from DispatchTrip
            prev_state = vehicle.vehicle_state.__class__.__name__
            msg = f"ServicingTrip called for vehicle {vehicle.id} but previous state ({prev_state}) is not DispatchTrip as required"
            error = SimulationStateError(msg)
            return error, None
        elif not self.request.membership.grant_access_to_membership(vehicle.membership):
            msg = f"vehicle {vehicle.id} attempting to service request {self.request.id} with mis-matched memberships/fleets"
            return SimulationStateError(msg), None
        else:
            pickup_error, pickup_sim = pick_up_trip(sim, env, self.vehicle_id, self.request.id)
            if pickup_error:
                return pickup_error, None
            else:
                enter_result = VehicleState.apply_new_vehicle_state(pickup_sim, self.vehicle_id, self)
                return enter_result

    def exit(self, sim: SimulationState, env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        """
        cannot call "exit" on ServicingTrip, must be exited via it's update method.
        the state is modeling a trip. exiting would mean dropping off passengers prematurely.
        this is only valid when falling OutOfService or when reaching the destination.
        both of these transitions occur during the update step of ServicingTrip.

        :param sim: the sim state
        :param env: the sim environment
        :return: None, None - cannot invoke "exit" on ServicingTrip
        """
        return None, None

    def _has_reached_terminal_state_condition(self, sim: SimulationState, env: Environment) -> bool:
        """
        ignored: this should be handled in the update phase when the length of the route is zero.

        :param sim: the sim state
        :param env: the sim environment
        :return: True if we have reached the base
        """
        return False

    def _enter_default_terminal_state(self,
                                      sim: SimulationState,
                                      env: Environment
                                      ) -> Tuple[Optional[Exception], Optional[Tuple[SimulationState, VehicleState]]]:
        """
        by default, Idle when we are in the terminal state

        :param sim: the sim state
        :param env: the sim environment
        :return: an exception due to failure or an optional updated simulation
        """

        next_state = Idle(self.vehicle_id)
        enter_error, enter_sim = next_state.enter(sim, env)
        if enter_error:
            return enter_error, None
        else:
            return None, (enter_sim, next_state)

    def _perform_update(self,
                        sim: SimulationState,
                        env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        """
        take a step along the route to the base

        :param sim: the simulation state
        :param env: the simulation environment
        :return: the sim state with vehicle moved
        """

        move_error, move_result = move(sim, env, self.vehicle_id, self.trip.route)
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
            updated_state = self._replace(route=updated_route)
            updated_vehicle = moved_vehicle.modify_vehicle_state(updated_state)
            error2, sim2 = simulation_state_ops.modify_vehicle(move_result.sim, updated_vehicle)

            if error2:
                return error2, None
            elif len(updated_route) == 0:
                # let's drop the passengers off during this time step and go Idle
                error3, sim3 = drop_off_trip(sim, env, self.vehicle_id, self.request)
                if error3:
                    return error3, None
                else:
                    idle_result = self._enter_default_terminal_state(sim3, env)
                    return idle_result
            else:
                return None, sim2
