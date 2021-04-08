from __future__ import annotations

from typing import Tuple, Optional, FrozenSet
import functools as ft

from hive.model.request import Request
from hive.model.vehicle.trip_phase import TripPhase
from hive.model.vehicle.vehicle import Vehicle, RequestId
from hive.state.vehicle_state.rerouted_pooling_trip import ReroutedPoolingTrip
from hive.state.vehicle_state.servicing_pooling_trip import ServicingPoolingTrip


def trip_plan_covers_previous(previous_state: ServicingPoolingTrip,
                              new_trip_plan: Tuple[Tuple[RequestId, TripPhase], ...]) -> bool:
    """
    checks that the incoming trip plan covers the previous plan

    :param previous_state: previous pooling trip state
    :param new_trip_plan: the proposed trip plan
    :return: True, if the plan is valid
    """
    prev_req_ids = set(map(lambda r_id, phase: r_id, previous_state.trip_plan))
    plan_req_ids = set(map(lambda r_id, phase: r_id, new_trip_plan))

    previous_plan_not_covered = len(prev_req_ids.difference(plan_req_ids)) > 0

    return previous_plan_not_covered


def trip_plan_ordering_is_valid(new_trip_plan: Tuple[Tuple[RequestId, TripPhase], ...],
                                previous_state: Optional[ServicingPoolingTrip] = None
                                ) -> bool:
    """
    checks that the incoming trip plan has a logical pickup and dropoff ordering

    :param previous_state: previous pooling trip state
    :param new_trip_plan: the proposed trip plan
    :return: True, if the plan is valid
    """
    # inspect previous state and test for coverage of requests/state

    boarded_req_ids = frozenset(map(lambda trip: trip.request.id, previous_state.trips)) \
        if previous_state else frozenset()

    def _test(acc: Tuple[bool, FrozenSet[str]],
              plan_step: Tuple[RequestId, TripPhase]) -> Tuple[bool, FrozenSet[str]]:
        is_good, boarded = acc
        if not is_good:
            return acc
        else:
            r_id, t = plan_step
            if t == TripPhase.PICKUP:
                updated_boarded = boarded.union([r_id])
                return True, updated_boarded
            else:
                if r_id in boarded:
                    updated_boarded = boarded.difference([r_id])
                    return True, updated_boarded
                else:
                    return False, frozenset()

    initial = (True, boarded_req_ids)
    is_valid, _ = ft.reduce(_test, new_trip_plan, initial)

    return is_valid


def create_reroute_pooling_trip(sim: 'SimulationState',
                                env: 'Environment',
                                vehicle: Vehicle,
                                trip_plan: Tuple[Tuple[RequestId, TripPhase], ...]
                                ) -> Tuple[Optional[Exception], Optional[ReroutedPoolingTrip]]:
    """
    constructs a new trip plan based on the provided requests.

    we may be carrying some passengers already. we may be diverting sooner or later
    along our trip plan. we must assume any request may be mid-flight or may not yet
    be picked up.

    :param sim: the sim state
    :param env: the sim environment
    :param vehicle: vehicle being re-routed
    :param trip_order: the proposed trip order from dispatch
    :param new_requests: the requests which are newly added to this pooling trip
    :return: the
    """

    # updated_trips = ft.reduce(
    #     lambda acc, r: acc.set(r.id, Trip(r, r.departure_time, (), r.passengers)),
    #     new_requests,
    #     vehicle.vehicle_state.trips
    # )
    # first_trip = updated_trips.get(TupleOps.head(trip_order))
    # sim.road_network.route()
