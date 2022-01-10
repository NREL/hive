from __future__ import annotations

import logging
from typing import NamedTuple, Tuple, TYPE_CHECKING, Optional
from uuid import uuid4

import immutables

from hive.model.request import Request
from hive.model.roadnetwork.route import Route
from hive.model.sim_time import SimTime
from hive.model.vehicle.trip_phase import TripPhase
from hive.runner.environment import Environment
from hive.state.vehicle_state import servicing_ops
from hive.state.vehicle_state.idle import Idle
from hive.state.vehicle_state.servicing_ops import get_active_pooling_trip, pick_up_trip, \
    update_active_pooling_trip, ActivePoolingTrip
from hive.state.vehicle_state.vehicle_state import VehicleState, VehicleStateInstanceId
from hive.state.vehicle_state.vehicle_state_ops import move
from hive.state.vehicle_state.vehicle_state_type import VehicleStateType
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

    instance_id: VehicleStateInstanceId

    @classmethod
    def build(
        cls,
        vehicle_id: VehicleId,
        trip_plan: Tuple[Tuple[RequestId, TripPhase], ...],
        boarded_requests: immutables.Map[RequestId, Request],
        departure_times: immutables.Map[RequestId, SimTime],
        routes: Tuple[Route, ...],
        num_passengers: int,
    ) -> ServicingPoolingTrip:
        return ServicingPoolingTrip(vehicle_id=vehicle_id,
                                    trip_plan=trip_plan,
                                    boarded_requests=boarded_requests,
                                    departure_times=departure_times,
                                    routes=routes,
                                    num_passengers=num_passengers,
                                    instance_id=uuid4())

    @property
    def vehicle_state_type(cls) -> VehicleStateType:
        return VehicleStateType.SERVICING_POOLING_TRIP

    @property
    def route(cls) -> Route:
        """
        makes this uniform with other "move" states to have a "route" property
        :return:
        """
        return cls.routes[0] if len(cls.routes) > 0 else ()
    
    def update_route(self, route: Route) -> ServicingPoolingTrip:
        tail = TupleOps.tail(self.routes)
        updated_routes = TupleOps.prepend(route, tail)
        return self._replace(routes=updated_routes)

    def update(self, sim: SimulationState,
               env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        return VehicleState.default_update(sim, env, self)

    def enter(self, sim: SimulationState,
              env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        """
        transition from DispatchTrip into a pooling trip service leg. this first frame of servicing
        a pooling trip should be happening at the start location of the first request in the pool,
        which should already be boarded (so, the first trip_phase is not to pick that request up).

        :param sim: the simulation state
        :param env: the simulation environment
        :return: an error, or, the sim with state entered
        """

        vehicle = sim.vehicles.get(self.vehicle_id)
        first_trip_plan_step, remaining_trip_plan = TupleOps.head_tail(self.trip_plan)
        first_req_id, first_trip_phase = first_trip_plan_step
        first_req = sim.requests.get(first_req_id)

        context = f"vehicle {self.vehicle_id} entering servicing pooling trip state"
        if vehicle is None:
            return SimulationStateError(f"vehicle note found; context: {context}"), None
        if first_req is None:
            return SimulationStateError(
                f"request {first_req_id} not found; context: {context}"), None
        elif not vehicle.vehicle_state.vehicle_state_type == VehicleStateType.DISPATCH_POOLING_TRIP:
            # the only supported transition into ServicingPoolingTrip comes from DispatchTrip
            prev_state = vehicle.vehicle_state.__class__.__name__
            msg = f"ServicingPoolingTrip called for vehicle {vehicle.id} but previous state ({prev_state}) is not DispatchTrip as required"
            error = SimulationStateError(msg)
            return error, None
        elif len(self.trip_plan) == 0:
            msg = f"vehicle {self.vehicle_id} attempting to enter a ServicingPoolingTrip state without any trip plan"
            error = SimulationStateError(msg)
            return error, None
        else:
            # pick up first request
            pickup_error, pickup_sim = servicing_ops.pick_up_trip(sim, env, self.vehicle_id,
                                                                  first_req_id)
            if pickup_error:
                result = SimulationStateError(
                    f"failed to pick up first trip in ServicingPoolingTrip {self}")
                result.__cause__ = pickup_error
                return result, None
            else:
                # enter ServicingPoolingTrip state with first request boarded
                vehicle_state_with_first_trip = self._replace(
                    boarded_requests=immutables.Map({first_req_id: first_req}),
                    departure_times=immutables.Map({first_req_id: sim.sim_time}),
                    num_passengers=len(first_req.passengers),
                    trip_plan=remaining_trip_plan)
                result = VehicleState.apply_new_vehicle_state(pickup_sim, self.vehicle_id,
                                                              vehicle_state_with_first_trip)
                return result

    def exit(self, next_state: VehicleState, sim: SimulationState,
             env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        """
        exit when there is no remaining trip_phase to complete

        :param sim: the sim state
        :param env: the sim environment
        :return: None, None - cannot invoke "exit" on ServicingPoolingTrip
        """
        if len(self.trip_plan) == 0:
            return None, sim
        elif next_state.vehicle_state_type == VehicleStateType.DISPATCH_POOLING_TRIP:
            # a pooling replanning can interrupt a ServicingPoolingTrip in process
            return None, sim
        else:
            return None, None

    def _has_reached_terminal_state_condition(self, sim: SimulationState, env: Environment) -> bool:
        """
        ignored: this should be handled in the update phase when the length of the final route is zero.

        :param sim: the simulation state
        :param env: the simulation environment
        :return: true if our trip is done
        """
        return len(self.trip_plan) == 0

    def _default_terminal_state(
            self, sim: SimulationState,
            env: Environment) -> Tuple[Optional[Exception], Optional[VehicleState]]:
        """
        give the default state to transition to after having met a terminal condition

        :param sim: the simulation state
        :param env: the simulation environment
        :return: an exception due to failure or the next_state after finishing a task
        """
        next_state = Idle.build(self.vehicle_id)
        return None, next_state

    def _perform_update(self, sim: SimulationState,
                        env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        """
        move forward on our trip, making pickups and dropoffs as needed

        :param sim: the simulation state
        :param env: the simulation environment
        :return: the vehicle after advancing in time on a servicing trip
        """

        # grab the current trip
        err1, active_trip = get_active_pooling_trip(self)
        if err1 is not None:
            response = SimulationStateError(
                f"failure during ServicingPoolingTrip._perform_update for vehicle {self.vehicle_id}"
            )
            response.__cause__ = err1
            return response, None
        else:
            # move forward in current trip plan
            move_error, move_sim = move(sim, env, self.vehicle_id)
            moved_vehicle = move_sim.vehicles.get(self.vehicle_id) if move_sim else None

            if move_error:
                response = SimulationStateError(
                    f"failure during ServicingPoolingTrip._perform_update for vehicle {self.vehicle_id}"
                )
                response.__cause__ = move_error
                return response, None
            elif not moved_vehicle:
                return SimulationStateError(f"vehicle {self.vehicle_id} not found"), None
            elif moved_vehicle.vehicle_state.vehicle_state_type == VehicleStateType.OUT_OF_SERVICE:
                return None, move_sim 
            else:
                # update the state of the pooling trip 
                result = update_active_pooling_trip(move_sim, env, self)
                return result
