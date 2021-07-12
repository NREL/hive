from __future__ import annotations

import logging
from typing import NamedTuple, Tuple, Optional, TYPE_CHECKING

import immutables

from hive.model.request import Request
from hive.model.roadnetwork.route import Route, route_cooresponds_with_entities
from hive.model.sim_time import SimTime
from hive.model.vehicle.trip_phase import TripPhase
from hive.runner.environment import Environment
from hive.state.simulation_state import simulation_state_ops
from hive.state.vehicle_state import vehicle_state_ops, dispatch_ops, servicing_ops
from hive.state.vehicle_state.servicing_pooling_trip import ServicingPoolingTrip
from hive.state.vehicle_state.vehicle_state import VehicleState
from hive.state.vehicle_state.vehicle_state_type import VehicleStateType
from hive.util import TupleOps
from hive.util.exception import SimulationStateError
from hive.util.typealiases import RequestId, VehicleId

if TYPE_CHECKING:
    from hive.state.simulation_state.simulation_state import SimulationState

log = logging.getLogger(__name__)


class DispatchPoolingTrip(NamedTuple, VehicleState):
    vehicle_id: VehicleId
    # this trip plan contains all phases, including the initial pickup
    trip_plan: Tuple[Tuple[RequestId, TripPhase], ...]
    # this is the route to the first pickup location
    route: Route
    # if this overrides a ServicingPoolingTrip state, we carry that state here as well
    boarded_requests: immutables.Map[RequestId, Request] = immutables.Map()
    departure_times: immutables.Map[RequestId, SimTime] = immutables.Map()
    num_passengers: int = 0

    @property
    def vehicle_state_type(cls) -> VehicleStateType:
        return VehicleStateType.DISPATCH_POOLING_TRIP

    def update(self, sim: SimulationState, env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        return VehicleState.default_update(sim, env, self)

    def enter(self, sim: 'SimulationState', env: 'Environment') -> Tuple[Optional[Exception], Optional['SimulationState']]:
        """
        checks that all requests exist. updates all requests to know that this vehicle is on it's way

        :param sim: the sim state
        :param env: the sim environment
        :return: an exception, or a sim state, or (None, None) if the request isn't there anymore
        """
        first_stop = TupleOps.head_optional(self.trip_plan)
        if first_stop is None:
            log.debug(f"DispatchPoolingTrip.enter called with empty trip_plan")
            return None, None
        else:
            req_ids, _ = tuple(zip(*self.trip_plan))
            vehicle = sim.vehicles.get(self.vehicle_id)
            reqs_exist_and_match_membership = dispatch_ops.requests_exist_and_match_membership(sim, vehicle, req_ids)
            first_req_id, first_phase = first_stop
            first_req = sim.requests.get(first_req_id)
            is_valid = route_cooresponds_with_entities(self.route, vehicle.link, first_req.origin_link) if vehicle and first_req else False

            if not vehicle:
                error = SimulationStateError(f"vehicle {self.vehicle_id} does not exist")
                return error, None
            elif not reqs_exist_and_match_membership:
                # not an error - may have been picked up; or, bad dispatcher.. fail silently
                return None, None
            elif not is_valid:
                log.debug(f"bad route to connect vehicle {vehicle.id} to request {first_req.id}")
                return None, None
            else:
                error, updated_sim = dispatch_ops.modify_vehicle_assignment(sim, self.vehicle_id, req_ids)
                if error:
                    return error, None
                else:
                    result = VehicleState.apply_new_vehicle_state(updated_sim, self.vehicle_id, self)
                    return result

    def exit(self, sim: 'SimulationState', env: 'Environment') -> Tuple[Optional[Exception], Optional['SimulationState']]:
        """
        release the vehicle from the requests it was dispatched to

        :param sim: the simulation state
        :param env: the simulation environment
        :return: an error, or, the updated simulation state, where the requests are no longer awaiting this vehicle
        """
        req_ids, _ = tuple(zip(*self.trip_plan))
        result = dispatch_ops.modify_vehicle_assignment(sim, self.vehicle_id, req_ids, unassign=True)
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
                                      env: Environment) -> Tuple[Optional[Exception], Optional[Tuple[SimulationState, VehicleState]]]:
        """
        by default, transition to a ServicingPoolingTrip state (if possible), else Idle if the conditions are not correct.

        :param sim: the sim state
        :param env: the sim environment
        :return:  an exception due to failure or an optional updated simulation
        """

        vehicle = sim.vehicles.get(self.vehicle_id)
        first_stop, remaining_trip_plan = TupleOps.head_tail(self.trip_plan)

        if first_stop is None:
            log.debug(f"DispatchPoolingTrip.enter called with empty trip_plan")
            return None, None
        else:
            # confirm we are at the pickup location and first request is still there
            first_req_id, _ = first_stop
            first_req = sim.requests.get(first_req_id)
            if first_req and first_req.geoid != vehicle.geoid:  # todo: check this is a PICKUP phase, report state corruption
                locations = f"{first_req.geoid} != {vehicle.geoid}"
                message = f"vehicle {self.vehicle_id} ended dispatch trip to request {first_req_id} " + \
                          f"but locations do not match: {locations}. sim_time: {sim.sim_time}"
                return SimulationStateError(message), None
            else:
                # perform pickup action, removing request from the simulation. compute routes first!
                routes = dispatch_ops.create_routes(sim, self.trip_plan)
                pickup_error, pickup_sim = servicing_ops.pick_up_trip(sim, env, self.vehicle_id, first_req_id)
                if pickup_error:
                    return pickup_error, None
                else:
                    # create servicing state, with first request PICKUP event consumed
                    updated_trip_plan = TupleOps.tail(self.trip_plan)
                    boarded_requests = immutables.Map({first_req_id: first_req})
                    departure_times = immutables.Map({first_req_id: sim.sim_time})
                    num_passengers = len(first_req.passengers)

                    servicing_pooling_state = ServicingPoolingTrip(
                        vehicle_id=self.vehicle_id,
                        trip_plan=updated_trip_plan,
                        boarded_requests=boarded_requests,
                        departure_times=departure_times,
                        routes=routes,
                        num_passengers=num_passengers
                    )

                    enter_error, enter_sim = VehicleState.apply_new_vehicle_state(pickup_sim, self.vehicle_id, servicing_pooling_state)
                    if enter_error:
                        return enter_error, None
                    else:
                        return None, (enter_sim, servicing_pooling_state)

    def _perform_update(self,
                        sim: SimulationState,
                        env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        """
        take a step along the route to the first request

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
        elif moved_vehicle.vehicle_state.vehicle_state_type == VehicleStateType.OUT_OF_SERVICE:
            return None, move_result.sim
        else:
            # update moved vehicle's state (holding the route)
            updated_state = self._replace(route=move_result.route_traversal.remaining_route)
            updated_vehicle = moved_vehicle.modify_vehicle_state(updated_state)
            return simulation_state_ops.modify_vehicle(move_result.sim, updated_vehicle)
