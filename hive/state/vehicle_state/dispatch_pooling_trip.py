from __future__ import annotations

import logging
from typing import NamedTuple, Tuple, Optional, TYPE_CHECKING
from uuid import uuid4

import immutables

from hive.model.request import Request
from hive.model.roadnetwork.route import Route, route_cooresponds_with_entities
from hive.model.sim_time import SimTime
from hive.model.vehicle.trip_phase import TripPhase
from hive.runner.environment import Environment
from hive.state.simulation_state import simulation_state_ops
from hive.state.vehicle_state import vehicle_state_ops, dispatch_ops, servicing_ops
from hive.state.vehicle_state.servicing_pooling_trip import ServicingPoolingTrip
from hive.state.vehicle_state.vehicle_state import VehicleState, VehicleStateInstanceId
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

    # if we are re-planning a current ServicingPoolingTrip, we include this state
    boarded_requests: immutables.Map[RequestId, Request]
    departure_times: immutables.Map[RequestId, SimTime]
    num_passengers: int

    instance_id: VehicleStateInstanceId

    @classmethod
    def build(cls,
              vehicle_id: VehicleId,
              trip_plan: Tuple[Tuple[RequestId, TripPhase], ...],
              route: Route,
              boarded_requests: immutables.Map[RequestId, Request] = immutables.Map(),
              departure_times: immutables.Map[RequestId, SimTime] = immutables.Map(),
              num_passengers: int = 0) -> DispatchPoolingTrip:
        return cls(vehicle_id=vehicle_id,
                   trip_plan=trip_plan,
                   route=route,
                   boarded_requests=boarded_requests,
                   departure_times=departure_times,
                   num_passengers=num_passengers,
                   instance_id=uuid4())

    @property
    def vehicle_state_type(cls) -> VehicleStateType:
        return VehicleStateType.DISPATCH_POOLING_TRIP
    
    def update_route(self, route: Route) -> DispatchPoolingTrip:
        return self._replace(route=route)

    def update(self, sim: SimulationState,
               env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        return VehicleState.default_update(sim, env, self)

    def enter(self, sim: 'SimulationState',
              env: 'Environment') -> Tuple[Optional[Exception], Optional['SimulationState']]:
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
            reqs_exist_and_match_membership = dispatch_ops.requests_exist_and_match_membership(
                sim, vehicle, req_ids)
            first_req_id, first_phase = first_stop
            first_req = sim.requests.get(first_req_id)
            is_valid = route_cooresponds_with_entities(
                self.route, vehicle.position,
                first_req.origin_position) if vehicle and first_req else False

            context = f"vehicle {self.vehicle_id} entering dispatch pooling state"
            if not vehicle:
                error = SimulationStateError(f"vehicle does not exist; context: {context}")
                return error, None
            elif not reqs_exist_and_match_membership:
                # not an error - may have been picked up; or, bad dispatcher.. fail silently
                return None, None
            elif not is_valid:
                log.debug(f"bad route to connect vehicle {vehicle.id} to request {first_req.id}")
                return None, None
            else:
                error, updated_sim = dispatch_ops.modify_vehicle_assignment(
                    sim, self.vehicle_id, req_ids)
                if error:
                    response = SimulationStateError(
                        f"failure during DispatchPoolingTrip.enter for vehicle {self.vehicle_id}")
                    response.__cause__ = error
                    return response, None
                else:
                    result = VehicleState.apply_new_vehicle_state(updated_sim, self.vehicle_id,
                                                                  self)
                    return result

    def exit(self, next_state: VehicleState, sim: SimulationState,
             env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        """
        release the vehicle from the requests it was dispatched to

        :param sim: the simulation state
        :param env: the simulation environment
        :return: an error, or, the updated simulation state, where the requests are no longer awaiting this vehicle
        """
        req_ids, _ = tuple(zip(*self.trip_plan))
        result = dispatch_ops.modify_vehicle_assignment(sim,
                                                        self.vehicle_id,
                                                        req_ids,
                                                        unassign=True)
        return result

    def _has_reached_terminal_state_condition(self, sim: SimulationState, env: Environment) -> bool:
        """
        this terminates when we reach a base

        :param sim: the sim state
        :param env: the sim environment
        :return: True if we have reached the base
        """
        return len(self.route) == 0

    def _default_terminal_state(
            self, sim: SimulationState,
            env: Environment) -> Tuple[Optional[Exception], Optional[VehicleState]]:
        """
        give the default state to transition to after having met a terminal condition

        :param sim: the simulation state
        :param env: the simulation environment
        :return: an exception due to failure or the next_state after finishing a task
        """

        # create servicing state, with first request PICKUP event consumed
        routes = dispatch_ops.create_routes(sim, self.trip_plan)

        servicing_pooling_state = ServicingPoolingTrip.build(vehicle_id=self.vehicle_id,
                                                             trip_plan=self.trip_plan,
                                                             routes=routes,
                                                             boarded_requests=self.boarded_requests,
                                                             departure_times=self.departure_times,
                                                             num_passengers=self.num_passengers)
        return None, servicing_pooling_state

    def _perform_update(self, sim: SimulationState,
                        env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        """
        take a step along the route to the first request

        :param sim: the simulation state
        :param env: the simulation environment
        :return: the sim state with vehicle moved
        """
        move_error, move_sim = vehicle_state_ops.move(sim, env, self.vehicle_id)

        if move_error:
            response = SimulationStateError(
                f"failure during DispatchPoolingTrip._perform_update for vehicle {self.vehicle_id}")
            response.__cause__ = move_error
            return response, None
        else:
            return None, move_sim
