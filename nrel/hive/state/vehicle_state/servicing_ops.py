from __future__ import annotations
from dataclasses import replace

from typing import Optional, Tuple, TYPE_CHECKING, NamedTuple

from nrel.hive.model.request import Request
from nrel.hive.model.roadnetwork.route import Route
from nrel.hive.model.vehicle.trip_phase import TripPhase
from nrel.hive.model.vehicle.vehicle import Vehicle
from nrel.hive.reporting.vehicle_event_ops import (
    report_pickup_request,
    report_dropoff_request,
)
from nrel.hive.runner import Environment
from nrel.hive.state.vehicle_state.vehicle_state_type import VehicleStateType
from nrel.hive.state.simulation_state import simulation_state_ops
from nrel.hive.state.simulation_state.simulation_state import SimulationState
from nrel.hive.state.simulation_state.simulation_state_ops import modify_vehicle
from nrel.hive.util import RequestId, TupleOps, SimulationStateError, VehicleId

if TYPE_CHECKING:
    from nrel.hive.state.vehicle_state.servicing_pooling_trip import ServicingPoolingTrip


class ActivePoolingTrip(NamedTuple):
    request_id: RequestId
    trip_phase: TripPhase
    route: Route


def get_active_pooling_trip(
    vehicle_state: ServicingPoolingTrip,
) -> Tuple[Optional[Exception], Optional[ActivePoolingTrip]]:
    """
    helper to grab the currently-active trip

    :param vehicle_state: the servicing state to inspect
    :return: the active pooling trip we are servicing
    """

    first_trip = TupleOps.head_optional(vehicle_state.trip_plan)
    first_route = TupleOps.head_optional(vehicle_state.routes)
    if first_trip is None:
        error = SimulationStateError(
            f"attempting to grab the active request in ServicingPoolingTrip for vehicle {vehicle_state.vehicle_id} but request plan is empty"
        )
        return error, None
    elif first_route is None:
        error = SimulationStateError(
            f"attempting to grab the active request in ServicingPoolingTrip for vehicle {vehicle_state.vehicle_id} but route plan is empty"
        )
        return error, None
    else:
        request_id, trip_phase = first_trip
        active_pooling_trip = ActivePoolingTrip(request_id, trip_phase, first_route)
        return None, active_pooling_trip


def complete_trip_phase(
    sim: SimulationState,
    env: Environment,
    vehicle: Vehicle,
    active_trip: ActivePoolingTrip,
) -> Tuple[Optional[Exception], Optional[SimulationState]]:
    """
    performs the action associated with closing out a trip phase.

    invariant: the Vehicle must be in a ServicingPoolingTrip state!

    :param sim: the simulation state
    :param env: the simulation environment
    :param vehicle: the vehicle
    :param active_trip: the active pooling trip phase to close out
    :return: an error, or, the updated simulation state
    """

    if not vehicle.vehicle_state.vehicle_state_type == VehicleStateType.SERVICING_POOLING_TRIP:
        return (
            Exception(
                f"vehicle state is not ServicingPoolingTrip but {type(vehicle.vehicle_state)}"
            ),
            None,
        )
    else:
        vehicle_state: ServicingPoolingTrip = vehicle.vehicle_state  # type: ignore

    updated_trip_plan = TupleOps.tail(vehicle_state.trip_plan)
    updated_routes = TupleOps.tail(vehicle_state.routes)
    if active_trip.trip_phase == TripPhase.PICKUP:
        # perform pickup operation and update remaining route plan
        request = sim.requests.get(active_trip.request_id)
        if request is None:
            return (
                SimulationStateError(f"request {active_trip.request_id} not found"),
                None,
            )
        else:
            err2, sim2 = pick_up_trip(sim, env, vehicle.id, request.id)
            if err2 is not None:
                response = SimulationStateError(
                    f"failure completing trip phase for vehicle {vehicle.id} during TripPhase.PICKUP"
                )
                response.__cause__ = err2
                return response, None
            elif sim2 is None:
                return None, None
            else:
                # add this request to the boarded vehicles
                updated_boarded_requests = vehicle_state.boarded_requests.set(request.id, request)
                updated_num_passengers = vehicle_state.num_passengers + len(request.passengers)
                updated_departure_times = vehicle_state.departure_times.set(
                    request.id, sim.sim_time
                )
                updated_vehicle_state = replace(
                    vehicle_state,
                    trip_plan=updated_trip_plan,
                    routes=updated_routes,
                    boarded_requests=updated_boarded_requests,
                    num_passengers=updated_num_passengers,
                    departure_times=updated_departure_times,
                )
                updated_vehicle = vehicle.modify_vehicle_state(updated_vehicle_state)
                result = modify_vehicle(sim2, updated_vehicle)
                return result

    elif active_trip.trip_phase == TripPhase.DROPOFF:
        # perform dropoff operation and update remaining route plan
        request = vehicle_state.boarded_requests.get(active_trip.request_id)
        if request is None:
            error = SimulationStateError(
                f"request {active_trip.request_id} should have boarded pooling with vehicle {vehicle.id} but not found"
            )
            return error, None
        else:
            # result = drop_off_trip(sim, env, vehicle.id, request)
            # return result
            err2, sim2 = drop_off_trip(sim, env, vehicle.id, request)
            if err2 is not None:
                response = SimulationStateError(
                    f"failure completing trip phase for vehicle {vehicle.id} during TripPhase.DROPOFF"
                )
                response.__cause__ = err2
                return response, None
            elif sim2 is None:
                return None, None
            else:
                # remove this request from the boarded vehicles
                updated_boarded_requests = vehicle_state.boarded_requests.delete(request.id)
                updated_num_passengers = vehicle_state.num_passengers - len(request.passengers)
                updated_vehicle_state = replace(
                    vehicle_state,
                    trip_plan=updated_trip_plan,
                    routes=updated_routes,
                    boarded_requests=updated_boarded_requests,
                    num_passengers=updated_num_passengers,
                )
                updated_vehicle = vehicle.modify_vehicle_state(updated_vehicle_state)
                result = modify_vehicle(sim2, updated_vehicle)
                return result
    else:
        return (
            SimulationStateError(f"invalid trip phase {active_trip.trip_phase}"),
            None,
        )


def update_active_pooling_trip(
    sim: SimulationState,
    env: Environment,
    vehicle_id: VehicleId,
) -> Tuple[Optional[Exception], Optional[SimulationState]]:
    """
    helper to update the route of the leading trip when no route changes are required

    :param vehicle_state:
    :return:
    """
    context = f"updating active pooling trip for vehicle {vehicle_id}"
    vehicle = sim.vehicles.get(vehicle_id)
    if vehicle is None:
        return (
            SimulationStateError(f"vehicle not found; context: {context}"),
            None,
        )
    if not vehicle.vehicle_state.vehicle_state_type == VehicleStateType.SERVICING_POOLING_TRIP:
        return Exception("can only update vehicles in ServicingPoolingTrip states"), None
    else:
        pooling_state: ServicingPoolingTrip = vehicle.vehicle_state  # type: ignore

    current_route = pooling_state.route
    if len(current_route) > 0:
        # vehicle still on current route, noop
        return None, sim
    else:
        # we reached the end of a route, so, we need to perform whatever trip phase
        # action is required and then update the vehicle state accordingly
        err1, active_trip = get_active_pooling_trip(pooling_state)
        if err1 is not None:
            response = SimulationStateError(
                f"failure during update_active_pooling_trip for vehicle {vehicle.id}"
            )
            response.__cause__ = err1
            return response, None
        elif active_trip is None:
            return None, None
        else:
            result = complete_trip_phase(sim, env, vehicle, active_trip)
            return result


def pick_up_trip(
    sim: SimulationState,
    env: Environment,
    vehicle_id: VehicleId,
    request_id: RequestId,
) -> Tuple[Optional[Exception], Optional[SimulationState]]:
    """
    has a vehicle pick up a trip and receive payment for it.

    :param sim: the sim state
    :param env: the sim environment
    :param vehicle_id: the vehicle picking up the request
    :param request_id: the request to pick up
    :return: an error, or, the sim with the request picked up by the vehicle
    """
    vehicle = sim.vehicles.get(vehicle_id)
    request = sim.requests.get(request_id)
    context = f"vehicle {vehicle_id} pickup trip for request {request_id}"
    if not vehicle:
        return (
            SimulationStateError(f"vehicle not found; context: {context}"),
            None,
        )
    elif not request:
        return (
            SimulationStateError(f"request not found; context: {context}"),
            None,
        )
    else:
        updated_vehicle = vehicle.receive_payment(request.value)
        (
            mod_error,
            maybe_sim_with_vehicle,
        ) = simulation_state_ops.modify_vehicle(sim, updated_vehicle)
        if mod_error:
            response = SimulationStateError(f"failure during pick_up_trip for vehicle {vehicle.id}")
            response.__cause__ = mod_error
            return response, None
        elif maybe_sim_with_vehicle is None:
            return None, None
        else:
            try:
                report = report_pickup_request(updated_vehicle, request, maybe_sim_with_vehicle)
                env.reporter.file_report(report)
            except:
                # previous state may not be DispatchTrip (may not have expected attributes)
                pass
            return simulation_state_ops.remove_request(maybe_sim_with_vehicle, request_id)


def drop_off_trip(
    sim: SimulationState,
    env: Environment,
    vehicle_id: VehicleId,
    request: Request,
) -> Tuple[Optional[Exception], Optional[SimulationState]]:
    """
    handles the dropping off of passengers, which is really mostly a validation
    step followed by a logging step.

    :param sim: the sim state
    :param env: the sim environment
    :param vehicle_id: vehicle dropping off the trip
    :param trip: the trip to drop off
    :return: an exception due to failure or the simulation state
    """

    vehicle = sim.vehicles.get(vehicle_id)
    context = f"vehicle {vehicle_id} dropoff trip for request {request.id}"
    if not vehicle:
        return (
            SimulationStateError(f"vehicle not found; context: {context}"),
            None,
        )
    else:
        # confirm each passenger has reached their destination
        for passenger in request.passengers:
            if passenger.destination != vehicle.geoid:
                locations = f"{passenger.destination} != {vehicle.geoid}"
                message = f"vehicle {vehicle_id} dropping off passenger {passenger.id} but location is wrong: {locations}"
                return SimulationStateError(message), None

        report = report_dropoff_request(vehicle, sim, request)
        env.reporter.file_report(report)

        return None, sim
