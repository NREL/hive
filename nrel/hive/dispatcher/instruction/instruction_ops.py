from __future__ import annotations

import functools as ft
import logging
from typing import Tuple, Optional, FrozenSet, TYPE_CHECKING

from nrel.hive.model.vehicle.trip_phase import TripPhase
from nrel.hive.model.vehicle.vehicle import RequestId

if TYPE_CHECKING:
    from nrel.hive.state.simulation_state.simulation_state import SimulationState
    from nrel.hive.state.vehicle_state.servicing_pooling_trip import ServicingPoolingTrip

log = logging.getLogger(__name__)


def trip_plan_covers_previous(
    previous_state: ServicingPoolingTrip,
    new_trip_plan: Tuple[Tuple[RequestId, TripPhase], ...],
) -> bool:
    """
    checks that the incoming trip plan covers the previous plan

    :param previous_state: previous pooling trip state
    :param new_trip_plan: the proposed trip plan
    :return: True, if the plan is valid
    """
    prev_req_ids = set(map(lambda rid_and_phase: rid_and_phase[0], previous_state.trip_plan))
    plan_req_ids = set(map(lambda rid_and_phase: rid_and_phase[0], new_trip_plan))

    previous_plan_not_covered = len(prev_req_ids.difference(plan_req_ids)) > 0

    return previous_plan_not_covered


def trip_plan_ordering_is_valid(
    new_trip_plan: Tuple[Tuple[RequestId, TripPhase], ...],
    previous_state: ServicingPoolingTrip,
) -> bool:
    """
    checks that the incoming trip plan has a logical pickup and dropoff ordering and that
    no passengers are left on the vehicle after all steps in the trip plan.

    :param previous_state: previous pooling trip state
    :param new_trip_plan: the proposed trip plan
    :return: True, if the plan is valid
    """
    # inspect previous state and test for coverage of requests/state

    boarded_req_ids = (
        frozenset(map(lambda trip: trip[0], previous_state.trip_plan))
        if previous_state
        else frozenset()
    )

    # traverses the new trip plan, confirming that pickup and dropoff orders are correct,
    # and that, at the end, all trips are dropped off
    def _test(
        acc: Tuple[bool, FrozenSet[str]],
        plan_step: Tuple[RequestId, TripPhase],
    ) -> Tuple[bool, FrozenSet[str]]:
        is_good, boarded = acc
        if not is_good:
            return acc
        else:
            r_id, t = plan_step
            if t == TripPhase.PICKUP:
                updated_boarded = boarded.union([r_id])
                return True, updated_boarded
            elif t == TripPhase.DROPOFF:
                if r_id in boarded:
                    updated_boarded = boarded.difference([r_id])
                    return True, updated_boarded
                else:
                    return False, frozenset()
            else:
                # unknown trip phase, throw?
                log.error(f"trip for request {r_id} has invalid TripPhase {t}")
                return False, frozenset()

    initial = (True, boarded_req_ids)
    has_valid_order, final_boarding_state = ft.reduce(_test, new_trip_plan, initial)
    no_passengers_at_end_of_trip_plan = len(final_boarding_state) == 0

    return has_valid_order and no_passengers_at_end_of_trip_plan


def trip_plan_all_requests_allow_pooling(
    sim: SimulationState, trip_plan: Tuple[Tuple[RequestId, TripPhase], ...]
) -> Optional[str]:
    """
    confirm that each request in the trip plan allows pooling

    :param sim: the sim state
    :param trip_plan: the proposed trip plan from dispatch
    :return: None if all requests do allow pooling, otherwise, a specific error
    """

    def _test_req(
        test_errors: Tuple[Tuple[str, ...], Tuple[str, ...]], r_id: RequestId
    ) -> Tuple[Tuple[str, ...], Tuple[str, ...]]:
        sim_error_ids, pool_error_ids = test_errors
        req = sim.requests.get(r_id)
        if req is None:
            updated_sim_error_ids = sim_error_ids + (r_id,)
            return updated_sim_error_ids, pool_error_ids
        elif not req.allows_pooling:
            updated_pool_error_ids = sim_error_ids + (r_id,)
            return sim_error_ids, updated_pool_error_ids
        else:
            return test_errors

    req_ids, _ = frozenset(zip(*trip_plan))
    req_ids_unique = frozenset(req_ids)
    initial_errors: Tuple[Tuple[str, ...], Tuple[str, ...]] = ((), ())
    sim_error_req_ids, pool_error_req_ids = ft.reduce(_test_req, req_ids_unique, initial_errors)
    if len(sim_error_req_ids) > 0 and len(pool_error_req_ids) > 0:
        msg = f"reqs not in sim: {sim_error_req_ids}; reqs which don't allow pooling: {pool_error_req_ids}"
        return msg
    elif len(sim_error_req_ids) > 0:
        msg = f"reqs not in sim: {sim_error_req_ids}"
        return msg
    elif len(pool_error_req_ids) > 0:
        msg = f"reqs which don't allow pooling: {pool_error_req_ids}"
        return msg
    else:
        return None


# def create_dispatch_pooling_trip(sim: 'SimulationState',
#                                  vehicle: Vehicle,
#                                  trip_plan: Tuple[Tuple[RequestId, TripPhase], ...]
#                                  ) -> Tuple[Optional[Exception], Optional[ServicingPoolingTrip]]:
#     """
#     create a vehicle state representing a new pooling trip plan.
#
#     this pooling state has been validated and so within this scope while constructing the route plan
#     we trust that the trip plan accounts for all trips already boarded.
#
#     :param sim: the sim state
#     :param vehicle: vehicle being re-routed
#     :param trip_plan: the proposed trip plan from dispatch
#     :return: the dispatch pooling trip state
#     """
#
#     # create each route for the route plan
#     def _create_route(acc: Tuple[Link, Tuple[Route, ...]],
#                       plan_step: Tuple[RequestId, TripPhase]) -> Tuple[Link, Tuple[Route, ...]]:
#         prev_link, solution = acc
#         req_id, t = plan_step
#         request = sim.requests.get(req_id)
#         if request is None:
#             log.error(f"attempting to build pooling trip with {req_id} which is not in the simulation")
#             return acc
#         else:
#             next_link = request.origin_link if t == TripPhase.PICKUP else request.destination_link
#             next_route = sim.road_network.route(prev_link, next_link)
#             next_routes = solution + (next_route, )
#             return next_link, next_routes
#
#     initial = (vehicle.geoid, ())
#     _, route_plan = ft.reduce(_create_route, trip_plan, initial)
#
#     req_ids, _ = tuple(zip(*trip_plan))
#     req_ids_unique = frozenset(req_ids)
#     reqs = immutables.Map({r_id: sim.requests.get(r_id) for r_id in req_ids_unique})
#     num_passengers = sum([len(r.passengers) for r in reqs.values()])
#
#     state = ServicingPoolingTrip.build(
#         vehicle_id=vehicle.id,
#         trip_plan=trip_plan,
#         trips=reqs,
#         routes=route_plan,
#         num_passengers=num_passengers
#     )
#     return None, state
