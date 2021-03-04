from __future__ import annotations

import logging
from typing import NamedTuple, Tuple, TYPE_CHECKING, Optional

import immutables

from hive.model.trip import Trip
from hive.state.simulation_state import simulation_state_ops
from hive.state.vehicle_state.idle import Idle
from hive.state.vehicle_state.out_of_service import OutOfService
from hive.state.vehicle_state.servicing_ops import get_active_pooling_trip, remove_completed_trip, enter_servicing_state, drop_off_trip
from hive.state.vehicle_state.vehicle_state import VehicleState
from hive.state.vehicle_state.vehicle_state_ops import move
from hive.util import SimulationStateError
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
        error0, active_trip = get_active_pooling_trip(self)
        if error0:
            return error0, None
        else:
            result = enter_servicing_state(sim, env, self.vehicle_id, active_trip, self)
            return result

    def exit(self, sim: 'SimulationState', env: 'Environment') -> Tuple[Optional[Exception], Optional['SimulationState']]:
        """
        cannot call "exit" on ServicingPoolingTrip, must be exited via it's update method.
        the state is modeling a trip. exiting would mean dropping off passengers prematurely.
        this is only valid when falling OutOfService or when reaching the destination.
        both of these transitions occur during the update step of ServicingPoolingTrip.

        :param sim: the sim state
        :param env: the sim environment
        :return: None, None - cannot invoke "exit" on ServicingPoolingTrip
        """
        return None, None

    def _has_reached_terminal_state_condition(self, sim: 'SimulationState', env: 'Environment') -> bool:
        error0, active_trip = get_active_pooling_trip(self)
        if error0:
            return False
        else:
            return len(self.trips) == 1 and len(active_trip.route) == 0

    def _enter_default_terminal_state(self, sim: 'SimulationState', env: 'Environment') -> Tuple[Optional[Exception],
                                                                                             Optional[Tuple['SimulationState', VehicleState]]]:
        next_state = Idle(self.vehicle_id)
        enter_error, enter_sim = next_state.enter(sim, env)
        if enter_error:
            return enter_error, None
        else:
            return None, (enter_sim, next_state)

    def _perform_update(self, sim: 'SimulationState', env: 'Environment') -> Tuple[Optional[Exception], Optional['SimulationState']]:
        error0, active_trip = get_active_pooling_trip(self)
        if error0:
            return error0, None
        else:
            error1, move_result = move(sim, env, self.vehicle_id, active_trip.route)
            moved_vehicle = move_result.sim.vehicles.get(self.vehicle_id) if move_result else None

            if error1:
                return error1, None
            elif not moved_vehicle:
                return SimulationStateError(f"vehicle {self.vehicle_id} not found"), None
            elif isinstance(moved_vehicle.vehicle_state, OutOfService):
                return None, move_result.sim
            else:
                # update moved vehicle's state (holding the route)
                moved_trip = active_trip.update_route(move_result.route_traversal.remaining_route)
                moved_trips = self.trips.update({active_trip.request_id, moved_trip})
                moved_state = self._replace(trips=moved_trips)
                moved_vehicle = moved_vehicle.modify_vehicle_state(moved_state)

                # have we reached our (current) destination? (lead trip.route is empty)
                if len(moved_trip.route) != 0:
                    # nope, still driving towards that destination
                    result = simulation_state_ops.modify_vehicle(move_result.sim, moved_vehicle)
                    return result
                else:
                    # drop these passengers off (triggers a report)
                    error2, sim2 = drop_off_trip(sim, env, self.vehicle_id, moved_trip)
                    if error2:
                        return error2, None
                    else:
                        # since this is a pooling trip, remove the moved_trip
                        error3, remove_result = remove_completed_trip(move_result.sim, env, self.vehicle_id)
                        if error3:
                            return error3, None
                        else:
                            # if that was our last pooling trip, then we can go Idle
                            sim3, remaining_trips = remove_result
                            if len(self.trips) == 0:
                                next_state = Idle(self.vehicle_id)
                                result = next_state.enter(sim, env)
                                return result
                            else:
                                return None, sim3
