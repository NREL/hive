from __future__ import annotations

import logging
from typing import NamedTuple, Tuple, TYPE_CHECKING, Optional

import immutables

from hive.model.roadnetwork.route import Route
from hive.model.trip import Trip
from hive.runner import Environment
from hive.state.simulation_state import simulation_state_ops
from hive.state.simulation_state.simulation_state import SimulationState
from hive.state.vehicle_state.out_of_service import OutOfService
from hive.state.vehicle_state.servicing_ops import enter_re_routed_pooling_state, get_active_pooling_trip
from hive.state.vehicle_state.servicing_pooling_trip import ServicingPoolingTrip
from hive.state.vehicle_state.vehicle_state import VehicleState
from hive.state.vehicle_state.vehicle_state_ops import move
from hive.util import SimulationStateError
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
    re_route: Route
    trips: immutables.Map[RequestId, Trip]
    trip_order: Tuple[RequestId, ...]
    num_passengers: int

    def update(self, sim: 'SimulationState', env: 'Environment') -> Tuple[Optional[Exception], Optional['SimulationState']]:
        return VehicleState.default_update(sim, env, self)

    def enter(self, sim: 'SimulationState', env: 'Environment') -> Tuple[Optional[Exception], Optional['SimulationState']]:
        """
        confirm that the proposed re-routing is valid before entering this state
        :param sim: the simulation state
        :param env: the simulation environment
        :return: the simulation with the vehicle's state entered or an error
        """
        result = enter_re_routed_pooling_state(sim, env, self)
        return result

    def exit(self, sim: 'SimulationState', env: 'Environment') -> Tuple[Optional[Exception], Optional['SimulationState']]:
        """
        cannot call "exit" on ReroutedPoolingTrip, must be exited via it's update method.
        the state is modeling a trip. exiting would mean dropping off passengers prematurely.
        this is only valid when falling OutOfService or when reaching the destination.
        both of these transitions occur during the update step.

        :param sim: the sim state
        :param env: the sim environment
        :return: None, None - cannot invoke "exit" on ReroutedPoolingTrip
        """
        return None, None

    def _has_reached_terminal_state_condition(self,
                                              sim: SimulationState,
                                              env: Environment
                                              ) -> bool:
        """
        we are done rerouting if our re-routing path is empty

        :param sim: the sim state
        :param env: the sim environment
        :return:
        """
        end_of_reroute_trip = len(self.re_route) == 0
        return end_of_reroute_trip

    def _enter_default_terminal_state(self,
                                      sim: SimulationState,
                                      env: Environment
                                      ) -> Tuple[Optional[Exception], Optional[Tuple[SimulationState, VehicleState]]]:
        """
        if we have finished our re-routing trip, we default into the ServicingPoolingTrip state.
        this should likely never be called, as we perform this transition in the update method
        as well.

        :param sim: the sim state
        :param env: the sim environment
        :return: sim with this vehicle in a ServicingPoolingTrip state, or, an error
        """
        next_state = ServicingPoolingTrip(
            vehicle_id=self.vehicle_id,
            trips=self.trips,
            trip_order=self.trips,
            num_passengers=self.num_passengers
        )
        enter_error, enter_sim = next_state.enter(sim, env)
        if enter_error:
            return enter_error, None
        else:
            return None, (enter_sim, next_state)

    def _perform_update(self,
                        sim: SimulationState,
                        env: Environment
                        ) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        """
        move forward on our re-routing trip

        :param sim: the simulation state
        :param env: the simulation environment
        :return: the vehicle after advancing in time on re-routing
        """
        error1, move_result = move(sim, env, self.vehicle_id, self.re_route)
        moved_vehicle = move_result.sim.vehicles.get(self.vehicle_id) if move_result else None
        if error1:
            return error1, None
        elif not moved_vehicle:
            return SimulationStateError(f"vehicle {self.vehicle_id} not found"), None
        elif isinstance(moved_vehicle.vehicle_state, OutOfService):
            return None, move_result.sim
        else:
            # update moved vehicle's state
            moved_route = move_result.route_traversal.remaining_route
            moved_state = self._replace(re_route=moved_route)
            moved_vehicle = moved_vehicle.modify_vehicle_state(moved_state)

            # have we reached our (current) destination? (lead trip.route is empty)
            if len(moved_route) != 0:
                # nope, still driving towards that destination
                result = simulation_state_ops.modify_vehicle(move_result.sim, moved_vehicle)
                return result
            else:
                # transition back to a ServicingPoolingTrip state
                next_state = ServicingPoolingTrip(
                    vehicle_id=self.vehicle_id,
                    trips=self.trips,
                    trip_order=self.trips,
                    num_passengers=self.num_passengers
                )
                enter_error, enter_sim = next_state.enter(sim, env)
                if enter_error:
                    return enter_error, None
                else:
                    return None, enter_sim
