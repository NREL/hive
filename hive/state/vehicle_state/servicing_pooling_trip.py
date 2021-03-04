from __future__ import annotations

import logging
from typing import NamedTuple, Tuple, TYPE_CHECKING, Optional

import immutables

from hive.model.roadnetwork.route import route_cooresponds_with_entities
from hive.model.trip import Trip
from hive.runner import Environment
from hive.state.simulation_state.simulation_state import SimulationState
from hive.state.vehicle_state.vehicle_state import VehicleState
from hive.state.vehicle_state.vehicle_state_ops import pick_up_trip, enter_servicing_state
from hive.util import TupleOps, SimulationStateError
from hive.util.typealiases import RequestId, VehicleId

if TYPE_CHECKING:
    pass

log = logging.getLogger(__name__)


class ServicingPoolingTrip(NamedTuple, VehicleState):
    """
    a pooling trip is in service, for the given trips in the given trip_order.
    """
    vehicle_id: VehicleId
    trips: immutables.Map[RequestId, Trip]
    trip_order: Tuple[RequestId, ...]
    num_passengers: int

    def update(self, sim: 'SimulationState', env: 'Environment') -> Tuple[Optional[Exception], Optional['SimulationState']]:
        return VehicleState.default_update(sim, env, self)

    def enter(self, sim: 'SimulationState', env: 'Environment') -> Tuple[Optional[Exception], Optional['SimulationState']]:
        first_trip = TupleOps.head_optional(self.trip_order)
        trip = self.trips.get(first_trip.request_id) if first_trip else None
        if not first_trip:
            error = SimulationStateError(f"ServicingPoolingTrip has empty trip_order during enter method")
            return error, None
        elif not trip:
            error = SimulationStateError(f"trip with request id {first_trip} missing from trips collection {self.trips}")
            return error, None
        else:
            result = enter_servicing_state(sim, env, self.vehicle_id, trip, self)
            return result

    def exit(self, sim: 'SimulationState', env: 'Environment') -> Tuple[Optional[Exception], Optional['SimulationState']]:
        # ok, this is exiting the state, so, we should be able to empty ourselves of passengers
        # the logic should resemble ServicingTrip.exit
        pass

    def _has_reached_terminal_state_condition(self, sim: SimulationState, env: Environment) -> bool:
        # only one trip in our state and we are at it's destination
        pass

    def _enter_default_terminal_state(self, sim: SimulationState, env: Environment) -> Tuple[Optional[Exception],
                                                                                            Optional[Tuple[SimulationState, VehicleState]]]:
        # should be the same as ServicingTrip._enter_default_terminal_state
        pass

    def _perform_update(self, sim: SimulationState, env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        # - are we at a trip destination?
        #   - we need something similar to ServicingTrip.exit
        #   - we need to check if we have more trips
        # - otherwise it should be a typical move operation
        pass
