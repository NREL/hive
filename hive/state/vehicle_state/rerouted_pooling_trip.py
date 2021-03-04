from __future__ import annotations

import logging
from typing import NamedTuple, Tuple, TYPE_CHECKING, Optional

import immutables

from hive.model.roadnetwork.route import Route
from hive.model.trip import Trip
from hive.runner import Environment
from hive.state.simulation_state.simulation_state import SimulationState
from hive.state.vehicle_state.vehicle_state import VehicleState
from hive.util.typealiases import RequestId, VehicleId

if TYPE_CHECKING:
    pass

log = logging.getLogger(__name__)


class ReroutedPoolingTrip(NamedTuple, VehicleState):
    """
    a ServicingPoolingTrip has been interrupted and re-routed to the location of
    another request, which will join the trip.

    contains the (un-modified) trips of the previous ServicingPoolingTrip state,
    but, a new "trip_order" given by the dispatcher.

    once the re_route_request_id is reached:
    - if the request is still there, the new pick-up request will be lifted into a 'trip' tuple
    - if the request is gone, it will be removed from the trip_order
    - trip routes will be re-calculated based on the trip_order
    - the vehicle state will transition to ServicingPoolingTrip
    """
    vehicle_id: VehicleId
    re_route_request_id: RequestId
    re_route: Route
    trips: immutables.Map[RequestId, Trip]
    trip_order: Tuple[RequestId, ...]
    num_passengers: int

    def update(self, sim: 'SimulationState', env: 'Environment') -> Tuple[Optional[Exception], Optional['SimulationState']]:
        pass

    def enter(self, sim: 'SimulationState', env: 'Environment') -> Tuple[Optional[Exception], Optional['SimulationState']]:
        pass

    def exit(self, sim: 'SimulationState', env: 'Environment') -> Tuple[Optional[Exception], Optional['SimulationState']]:
        pass

    def _has_reached_terminal_state_condition(self, sim: SimulationState, env: Environment) -> bool:
        pass

    def _enter_default_terminal_state(self, sim: SimulationState, env: Environment) -> Tuple[Optional[Exception],
                                                                                             Optional[Tuple[SimulationState, VehicleState]]]:
        pass

    def _perform_update(self, sim: SimulationState, env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        pass
