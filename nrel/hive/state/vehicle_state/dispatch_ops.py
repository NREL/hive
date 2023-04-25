import functools as ft
from typing import Tuple, Optional

from nrel.hive.model.entity_position import EntityPosition
from nrel.hive.model.roadnetwork.route import Route
from nrel.hive.model.vehicle.trip_phase import TripPhase
from nrel.hive.model.vehicle.vehicle import Vehicle
from nrel.hive.state.simulation_state import simulation_state_ops
from nrel.hive.state.simulation_state.simulation_state import SimulationState
from nrel.hive.state.vehicle_state.dispatch_pooling_trip import DispatchPoolingTrip
from nrel.hive.state.vehicle_state.servicing_pooling_trip import ServicingPoolingTrip
from nrel.hive.util import (
    VehicleId,
    RequestId,
    iterators,
    SimulationStateError,
    TupleOps,
)


def requests_exist_and_match_membership(
    sim: SimulationState, vehicle: Vehicle, requests: Tuple[RequestId, ...]
) -> bool:
    """
    confirm that all requests currently exist in the system

    :param sim: the simulation state
    :param requests: the requests
    :return: True if all requests currently exist
    """

    def exists_and_match_membership(req_id):
        req = sim.requests.get(req_id)
        if req is None:
            return False
        else:
            membership_ok = (
                req.membership.grant_access_to_membership(vehicle.membership) if req else False
            )
            return membership_ok

    all_exist = all(map(exists_and_match_membership, requests))
    return all_exist


def modify_vehicle_assignment(
    sim: SimulationState,
    vehicle_id: VehicleId,
    requests: Tuple[RequestId, ...],
    unassign: bool = False,
) -> Tuple[Optional[Exception], Optional[SimulationState]]:
    """
    assign/un-assign this vehicle to each request. if a request does not exist, it is ignored.

    :param sim: the simulation state
    :param vehicle_id: the vehicle to assign
    :param requests: the requests to assign this vehicle to
    :param assign if true, un-assign the request, otherwise, assign
    :return: either an error, or, the updated simulation
    """

    def _modify(acc, req_id):
        err, sim = acc
        req = sim.requests.get(req_id) if sim is not None else None
        if err is not None:
            return acc
        elif req is None:
            return acc
        else:
            updated_req = (
                req.unassign_dispatched_vehicle()
                if unassign
                else req.assign_dispatched_vehicle(vehicle_id, sim.sim_time)
            )
            result = simulation_state_ops.modify_request(sim, updated_req)
            return result

    initial = None, sim
    result = ft.reduce(_modify, requests, initial)
    return result


def create_routes(
    sim: SimulationState, trip_plan: Tuple[Tuple[RequestId, TripPhase], ...]
) -> Tuple[Route, ...]:
    """
    creates routes between each phase of a trip plan. requires at least 2
    entries in the trip plan, which in the base case, would be a PICKUP followed
    by a DROPOFF.

    this does not include the access (dispatch) trip phase.

    :param sim: the simulation state
    :param env: the simulation environment
    :param trip_plan: the trip plan
    :return:
    """
    if len(trip_plan) < 2:
        return ()
    else:
        pairs = iterators.sliding(trip_plan, 2)

        def route_between(pair):
            src_tuple, dst_tuple = pair
            src_req, src_phase = src_tuple
            dst_req, dst_phase = dst_tuple
            src_link = get_position_for_phase(sim, src_req, src_phase)
            dst_link = get_position_for_phase(sim, dst_req, dst_phase)
            route = sim.road_network.route(src_link, dst_link)
            return route

        routes = tuple(map(route_between, pairs))
        return routes


def get_position_for_phase(
    sim: SimulationState, req_id: RequestId, trip_phase: TripPhase
) -> Optional[EntityPosition]:
    """
    gets the EntityPosition for the request based on the trip phase

    :param sim: the simulation state
    :param req_id: the request id
    :param trip_phase: pickup or dropoff phase of a trip
    :return: the EntityPosition for the Request at the specified TripPhase
    """
    req = sim.requests.get(req_id)
    if req is None:
        return None
    elif trip_phase == TripPhase.PICKUP:
        return req.position
    elif trip_phase == TripPhase.DROPOFF:
        return req.destination_position
    else:
        return None


def begin_or_replan_dispatch_pooling_state(
    sim: SimulationState,
    vehicle_id: VehicleId,
    trip_plan: Tuple[Tuple[RequestId, TripPhase], ...],
) -> Tuple[Optional[Exception], Optional[DispatchPoolingTrip]]:
    """
    create a DispatchPoolingTrip state. if the vehicle is currently in a ServicingPoolingTrip
    state, then carry over that state information here as well in the construction of the new state.

    :param sim: the simulation state
    :param vehicle_id: the vehicle to generate a new state for
    :param trip_plan: the trip plan to put into effect
    :return: a DispatchPoolingTrip state, or, an error
    """
    vehicle = sim.vehicles.get(vehicle_id)
    first_trip = TupleOps.head_optional(trip_plan)

    if vehicle is None:
        error = SimulationStateError(
            f"attempting to dispatch vehicle {vehicle_id} that does not exist"
        )
        return error, None
    elif first_trip is None:
        error = SimulationStateError(f"attempting to dispatch pooling trip with empty trip plan")
        return error, None
    else:
        first_req_id, first_phase = first_trip
        first_req_pos = get_position_for_phase(sim, first_req_id, first_phase)
        if first_req_pos is None:
            error = SimulationStateError(
                f"attempting to dispatch pooling trip to request {first_req_id} that does not exist in the sim"
            )
            return error, None
        else:
            route = sim.road_network.route(vehicle.position, first_req_pos)
            vehicle_state = vehicle.vehicle_state

            # todo: this should become a ServicingPoolingTrip instead
            #  - maybe we need a TripPhase.REPLANNING for the leg that is the interruption?
            if isinstance(vehicle_state, ServicingPoolingTrip):
                # already servicing pooling - copy over passenger state
                next_state = DispatchPoolingTrip.build(
                    vehicle_id,
                    trip_plan,
                    route,
                    vehicle_state.boarded_requests,
                    vehicle_state.departure_times,
                    vehicle_state.num_passengers,
                )
                return None, next_state
            else:
                # not already servicing pooling - just dispatch, don't carry over passenger state
                next_state = DispatchPoolingTrip.build(vehicle_id, trip_plan, route)
                return None, next_state
