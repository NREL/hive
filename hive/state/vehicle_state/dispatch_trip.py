from __future__ import annotations

import logging
from typing import NamedTuple, Tuple, Optional, TYPE_CHECKING

import immutables

from hive.model.passenger import board_vehicle
from hive.model.roadnetwork.route import Route, route_cooresponds_with_entities
from hive.model.vehicle.trip_phase import TripPhase
from hive.runner.environment import Environment
from hive.state.simulation_state import simulation_state_ops
from hive.state.simulation_state.simulation_state_ops import modify_request
from hive.state.vehicle_state import vehicle_state_ops
from hive.state.vehicle_state.idle import Idle
from hive.state.vehicle_state.out_of_service import OutOfService
from hive.state.vehicle_state.servicing_ops import create_servicing_state
from hive.state.vehicle_state.vehicle_state import VehicleState
from hive.util.exception import SimulationStateError
from hive.util.typealiases import RequestId, VehicleId

if TYPE_CHECKING:
    from hive.state.simulation_state.simulation_state import SimulationState

log = logging.getLogger(__name__)


class DispatchTrip(NamedTuple, VehicleState):
    vehicle_id: VehicleId
    request_id: RequestId
    route: Route

    def update(self, sim: SimulationState, env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        return VehicleState.default_update(sim, env, self)

    def enter(self, sim: SimulationState, env: Environment) -> Tuple[
        Optional[Exception], Optional[SimulationState]]:
        """
        checks that the request exists and if so, updates the request to know that this vehicle is on it's way

        :param sim: the sim state
        :param env: the sim environment
        :return: an exception, or a sim state, or (None, None) if the request isn't there anymore
        """
        vehicle = sim.vehicles.get(self.vehicle_id)
        request = sim.requests.get(self.request_id)
        is_valid = route_cooresponds_with_entities(self.route, vehicle.link, request.origin_link) if vehicle and request else False
        if not vehicle:
            error = SimulationStateError(f"vehicle {self.vehicle_id} does not exist")
            return error, None
        elif not request:
            # not an error - may have been picked up. fail silently
            return None, None
        elif not request.membership.grant_access_to_membership(vehicle.membership):
            msg = f"vehicle {vehicle.id} doesn't have access to request {request.id}"
            return SimulationStateError(msg), None
        elif not is_valid:
            return None, None
        else:
            updated_request = request.assign_dispatched_vehicle(self.vehicle_id, sim.sim_time)
            error, updated_sim = simulation_state_ops.modify_request(sim, updated_request)
            if error:
                return error, None
            else:
                result = VehicleState.apply_new_vehicle_state(updated_sim, self.vehicle_id, self)
                return result

    def exit(self, sim: SimulationState, env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        """
        release the vehicle from the request it was dispatched to

        :param sim: the simulation state
        :param env: the simulation environment
        :return: an error, or, the updated simulation state, where the request is no longer awaiting this vehicle
        """
        request = sim.requests.get(self.request_id)
        if request is None:
            # request doesn't exist, doesn't need to be updated
            return None, sim
        else:
            updated_request = request.unassign_dispatched_vehicle()
            # todo: possibly log this event here
            result = modify_request(sim, updated_request)
            return result

    def _has_reached_terminal_state_condition(self, sim: SimulationState, env: Environment) -> bool:
        """
        this terminates when we reach a base

        :param sim: the sim state
        :param env: the sim environment
        :return: True if we have reached the base
        """
        return len(self.route) == 0

    def _enter_default_terminal_state(self,
                                      sim: SimulationState,
                                      env: Environment
                                      ) -> Tuple[Optional[Exception], Optional[Tuple[SimulationState, VehicleState]]]:
        """
        by default, transition to a Servicing state (if possible), else Idle if the conditions are not correct.

        :param sim: the sim state
        :param env: the sim environment
        :return:  an exception due to failure or an optional updated simulation
        """
        vehicle = sim.vehicles.get(self.vehicle_id)
        request = sim.requests.get(self.request_id)
        if request and request.geoid != vehicle.geoid:
            locations = f"{request.geoid} != {vehicle.geoid}"
            message = f"vehicle {self.vehicle_id} ended dispatch trip to request {self.request_id} but locations do not match: {locations}. sim_time: {sim.sim_time}"
            return SimulationStateError(message), None
        elif not request:
            # request already got picked up or was cancelled; go an Idle state
            next_state = Idle(self.vehicle_id)
            enter_error, enter_sim = next_state.enter(sim, env)
            if enter_error:
                return enter_error, None
            else:
                return None, (enter_sim, next_state)
        else:
            next_state = create_servicing_state(sim, request, vehicle)

            # enter the servicing state
            enter_error, enter_sim = next_state.enter(sim, env)
            if enter_error:
                return enter_error, None
            elif not enter_sim:
                # can't enter ServicingTrip - request no longer exists! move to Idle
                idle_state = Idle(self.vehicle_id)
                idle_error, idle_sim = idle_state.enter(sim, env)
                if idle_error:
                    return idle_error, None
                else:
                    return None, (idle_sim, idle_state)
            else:
                return None, (enter_sim, next_state)

    def _perform_update(self,
                        sim: SimulationState,
                        env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        """
        take a step along the route to the request

        :param sim: the simulation state
        :param env: the simulation environment
        :return: the sim state with vehicle moved
        """

        move_error, move_result = vehicle_state_ops.move(sim, env, self.vehicle_id, self.route)
        moved_vehicle = move_result.sim.vehicles.get(self.vehicle_id) if move_result else None

        if move_error:
            return move_error, None
        elif not moved_vehicle:
            return SimulationStateError(f"vehicle {self.vehicle_id} not found"), None
        elif isinstance(moved_vehicle.vehicle_state, OutOfService):
            return None, move_result.sim
        else:
            # update moved vehicle's state (holding the route)
            updated_state = self._replace(route=move_result.route_traversal.remaining_route)
            updated_vehicle = moved_vehicle.modify_vehicle_state(updated_state)
            return simulation_state_ops.modify_vehicle(move_result.sim, updated_vehicle)
