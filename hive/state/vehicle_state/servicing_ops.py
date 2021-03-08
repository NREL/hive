from __future__ import annotations

from typing import Optional, Tuple, TYPE_CHECKING
from typing import Union
import functools as ft

from hive.model.roadnetwork.route import route_cooresponds_with_entities, routes_are_connected
from hive.model.trip import Trip
from hive.reporting.vehicle_event_ops import report_pickup_request, report_dropoff_request
from hive.runner import Environment
from hive.state.simulation_state import simulation_state_ops
from hive.state.simulation_state.simulation_state import SimulationState
from hive.state.vehicle_state.rerouted_pooling_trip import ReroutedPoolingTrip
from hive.state.vehicle_state.vehicle_state import VehicleState
from hive.util import RequestId, TupleOps, SimulationStateError, VehicleId
from hive.util.iterators import sliding

if TYPE_CHECKING:
    from hive.state.vehicle_state.servicing_trip import ServicingTrip
    from hive.state.vehicle_state.servicing_pooling_trip import ServicingPoolingTrip


def get_active_pooling_trip(
        vehicle_state: ServicingPoolingTrip
) -> Tuple[Optional[Exception], Optional[Trip]]:
    """
    helper to unpack the request id and trip data for the currently-active
    trip (the first trip in the trip_order)
    :param vehicle_state: the servicing state to inspect
    :return: the request id and trip, or, an error
    """

    first_trip = TupleOps.head_optional(vehicle_state.trip_order)
    trip = vehicle_state.trips.get(first_trip.request_id) if first_trip else None
    if not first_trip:
        error = SimulationStateError(f"ServicingPoolingTrip has empty trip_order during enter method")
        return error, None
    elif not trip:
        error = SimulationStateError(f"trip with request id {first_trip} missing from trips collection {vehicle_state.trips}")
        return error, None
    else:
        return None, trip


def pick_up_trip(sim: SimulationState,
                 env: Environment,
                 vehicle_id: VehicleId,
                 request_id: RequestId) -> Tuple[Optional[Exception], Optional[SimulationState]]:
    """
    has a vehicle pick up a trip and receive payment for it

    :param sim: the sim state
    :param env: the sim environment
    :param vehicle_id: the vehicle picking up the request
    :param request_id: the request to pick up
    :return: an error, or, the sim with the request picked up by the vehicle
    """
    vehicle = sim.vehicles.get(vehicle_id)
    request = sim.requests.get(request_id)
    if not vehicle:
        return SimulationStateError(f"vehicle {vehicle_id} not found"), None
    elif not request:
        return SimulationStateError(f"request {request_id} not found"), None
    else:
        updated_vehicle = vehicle.receive_payment(request.value)
        mod_error, maybe_sim_with_vehicle = simulation_state_ops.modify_vehicle(sim, updated_vehicle)
        if mod_error:
            return mod_error, None
        else:
            try:
                report = report_pickup_request(updated_vehicle, request, maybe_sim_with_vehicle)
                env.reporter.file_report(report)
            except:
                # previous state may not be DispatchTrip (may not have expected attributes)
                pass
            return simulation_state_ops.remove_request(maybe_sim_with_vehicle, request_id)


def drop_off_trip(sim: SimulationState,
                  env: Environment,
                  vehicle_id: VehicleId,
                  trip: Trip
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
    if not vehicle:
        return SimulationStateError(f"vehicle {vehicle_id} not found"), None
    else:
        # confirm each passenger has reached their destination
        for passenger in trip.passengers:
            if passenger.destination != vehicle.geoid:
                locations = f"{passenger.destination} != {vehicle.geoid}"
                message = f"vehicle {vehicle_id} dropping off passenger {passenger.id} but location is wrong: {locations}"
                return SimulationStateError(message), None

        report = report_dropoff_request(vehicle, sim, trip)
        env.reporter.file_report(report)

        return None, sim


def enter_servicing_state(sim: SimulationState,
                          env: Environment,
                          vehicle_id: VehicleId,
                          trip: Trip,
                          servicing_state: Union[ServicingTrip, ServicingPoolingTrip]
                          ) -> Tuple[Optional[Exception], Optional['SimulationState']]:
    """
    attempts to enter a servicing state, first validating
    :param sim: the simulation state
    :param env: the simulation environment
    :param vehicle_id: the vehicle servicing the trip
    :param trip: the trip to service
    :param servicing_state: a Servicing vehicle state
    :return: the simulation update result containing the effect of this transition
    """
    vehicle = sim.vehicles.get(vehicle_id)
    request = sim.requests.get(trip.request_id)
    is_valid = route_cooresponds_with_entities(
        trip.route,
        request.origin_link,
        request.destination_link
    ) if request and vehicle else False
    if not vehicle:
        return SimulationStateError(f"vehicle {vehicle_id} not found"), None
    if not request:
        # request was already picked up
        return None, None
    elif request and request.geoid != vehicle.geoid:
        locations = f"{request.geoid} != {vehicle.geoid}"
        message = f"vehicle {vehicle_id} ended trip to request {trip.request_id} but locations do not match: {locations}"
        return SimulationStateError(message), None
    elif not is_valid:
        return None, None
    elif not request.membership.grant_access_to_membership(vehicle.membership):
        msg = f"vehicle {vehicle.id} doesn't have access to request {trip.request_id}"
        return SimulationStateError(msg), None
    else:
        # request exists: pick up the trip and enter a ServicingTrip state
        pickup_error, pickup_sim = pick_up_trip(sim, env, vehicle_id, trip.request_id)
        if pickup_error:
            return pickup_error, None
        else:
            enter_result = VehicleState.apply_new_vehicle_state(pickup_sim, vehicle_id, servicing_state)
            return enter_result


def remove_completed_trip(sim: SimulationState,
                          env: Environment,
                          vehicle_id: VehicleId,
                          ) -> Tuple[Optional[Exception], Optional[Tuple[SimulationState, int]]]:
    """
    removes the first trip from a ServicingPoolingTrip state, because
    it has reached its destination.

    :param sim: the simulation state
    :param env: the simulation environment
    :param vehicle_id: the vehicle to remove it's completed trip
    :return: the updated simulation state along with the count of remaining trips
    """
    vehicle = sim.vehicles.get(vehicle_id)
    state = vehicle.vehicle_state if vehicle else None
    if state is None:
        error = SimulationStateError(f"vehicle {vehicle_id} not found in simulation state")
        return error, None
    elif not isinstance(state, ServicingPoolingTrip):
        error = SimulationStateError(f"vehicle {vehicle_id} state not pooling but attemping to remove it's oldest pooling trip")
        return error, None
    elif len(state.trips) == 0:
        error = SimulationStateError("remove first trip called on vehicle with no trips")
        return error, None
    else:
        vehicle = sim.vehicles.get(state.vehicle_id)
        removed_trip_request_id, updated_trip_order = TupleOps.head_tail(state.trip_order)
        updated_trips = state.trips.delete(removed_trip_request_id)
        updated_state = state._replace(
            trip_order=updated_trip_order,
            trips=updated_trips
        )
        updated_vehicle = vehicle.modify_vehicle_state(updated_state)
        error, result = simulation_state_ops.modify_vehicle(sim, updated_vehicle)
        return error, (result, len(updated_trips))


def enter_re_routed_pooling_state(sim: SimulationState,
                                  env: Environment,
                                  state: ReroutedPoolingTrip
                                  ) -> Tuple[Optional[Exception], Optional['SimulationState']]:
    """
    checks that the proposed new re routing state is correct by confirming
    the route plans are connected and ordered and that there are enough seats
    for all Passengers to ride.

    :param sim: the simulation state
    :param env: the simulation environment
    :param state: the vehicle state to apply
    :return: either the simulation with the updated state, or, an error
    """

    # do we have space for additional passengers?
    vehicle = sim.vehicles.get(state.vehicle_id)
    mech = env.mechatronics.get(vehicle.mechatronics_id) if vehicle else None
    current_passenger_count = sum([len(trip.passengers) for trip in state.trips.values()])
    req_id = state.re_route_request_id
    request = sim.requests.get(req_id)
    updated_passenger_count = len(request.passengers) + current_passenger_count if request else None
    has_space_for_new_passengers = updated_passenger_count <= mech.total_number_of_seats() if mech else False

    # are the routes correct? just check endpoint edge ids in order
    trips_ordered = (state.re_route,) + ft.reduce(lambda acc, r_id: acc + (state.trips.get(r_id),), state.trip_order, ())
    trips_match = all(ft.reduce(
        lambda acc, pair: acc + (routes_are_connected(pair[0], pair[1]),),
        sliding(trips_ordered, 2),
        ()
    ))

    if request is None:
        return SimulationStateError(f"proposed request {req_id} not found"), None
    elif not has_space_for_new_passengers:
        return SimulationStateError(f"request {req_id} attempting to board vehicle {state.vehicle_id} but not enough space"), None
    elif not trips_match:
        return SimulationStateError(f"proposed pooling re-route for request {req_id}, vehicle {state.vehicle_id} has invalid links"), None
    else:

        # looks good, let's switch to this re-routing state
        enter_result = VehicleState.apply_new_vehicle_state(sim, state.vehicle_id, state)
        return enter_result
