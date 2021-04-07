from __future__ import annotations

from typing import Tuple, Optional

from hive.model.request import Request
from hive.model.vehicle.vehicle import Vehicle, RequestId
from hive.state.vehicle_state.rerouted_pooling_trip import ReroutedPoolingTrip


def create_reroute_pooling_trip(sim: 'SimulationState',
                                env: 'Environment',
                                vehicle: Vehicle,
                                trip_order: Tuple[RequestId, ...],
                                new_requests: Tuple[Request, ...]
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
