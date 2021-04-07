from __future__ import annotations

import logging
from typing import NamedTuple, Tuple, Optional, TYPE_CHECKING

from hive.model.vehicle.trip import Trip
from hive.runner.environment import Environment
from hive.state.simulation_state import simulation_state_ops
from hive.state.vehicle_state.idle import Idle
from hive.state.vehicle_state.out_of_service import OutOfService
from hive.state.vehicle_state.servicing_ops import enter_servicing_state, drop_off_trip
from hive.state.vehicle_state.vehicle_state import VehicleState
from hive.state.vehicle_state.vehicle_state_ops import move
from hive.util.exception import SimulationStateError
from hive.util.typealiases import VehicleId

if TYPE_CHECKING:
    from hive.state.simulation_state.simulation_state import SimulationState

log = logging.getLogger(__name__)


class ServicingTrip(NamedTuple, VehicleState):
    vehicle_id: VehicleId
    trip: Trip

    def update(self,
               sim: SimulationState,
               env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        return VehicleState.default_update(sim, env, self)

    def enter(self,
              sim: SimulationState,
              env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        result = enter_servicing_state(sim, env, self.vehicle_id, self.trip, self)
        return result

    def exit(self, sim: SimulationState, env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        """
        cannot call "exit" on ServicingTrip, must be exited via it's update method.
        the state is modeling a trip. exiting would mean dropping off passengers prematurely.
        this is only valid when falling OutOfService or when reaching the destination.
        both of these transitions occur during the update step of ServicingTrip.

        :param sim: the sim state
        :param env: the sim environment
        :return: None, None - cannot invoke "exit" on ServicingTrip
        """
        return None, None

    def _has_reached_terminal_state_condition(self, sim: SimulationState, env: Environment) -> bool:
        """
        this terminates when we reach a base

        :param sim: the sim state
        :param env: the sim environment
        :return: True if we have reached the base
        """
        return len(self.trip.route) == 0

    def _enter_default_terminal_state(self,
                                      sim: SimulationState,
                                      env: Environment
                                      ) -> Tuple[Optional[Exception], Optional[Tuple[SimulationState, VehicleState]]]:
        """
        by default, Idle when we are in the terminal state

        :param sim: the sim state
        :param env: the sim environment
        :return: an exception due to failure or an optional updated simulation
        """

        next_state = Idle(self.vehicle_id)
        enter_error, enter_sim = next_state.enter(sim, env)
        if enter_error:
            return enter_error, None
        else:
            return None, (enter_sim, next_state)

    def _perform_update(self,
                        sim: SimulationState,
                        env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        """
        take a step along the route to the base

        :param sim: the simulation state
        :param env: the simulation environment
        :return: the sim state with vehicle moved
        """

        error1, sim1 = move(sim, env, self.vehicle_id, self.trip.route)
        moved_vehicle = sim1.sim.vehicles.get(self.vehicle_id) if sim1 else None

        if error1:
            return error1, None
        elif not moved_vehicle:
            return SimulationStateError(f"vehicle {self.vehicle_id} not found"), None
        elif isinstance(moved_vehicle.vehicle_state, OutOfService):
            return None, sim1.sim
        else:
            # update moved vehicle's state (holding the route)
            updated_trip = self.trip.update_route(sim1.route_traversal.remaining_route)
            updated_state = self._replace(trip=updated_trip)
            updated_vehicle = moved_vehicle.modify_vehicle_state(updated_state)
            error2, sim2 = simulation_state_ops.modify_vehicle(sim1.sim, updated_vehicle)

            if error2:
                return error2, None
            elif self._has_reached_terminal_state_condition(sim2, env):
                # let's drop the passengers off during this time step and go Idle
                error3, sim3 = drop_off_trip(sim, env, self.vehicle_id, self.trip)
                if error3:
                    return error3, None
                else:
                    idle_result = self._enter_default_terminal_state(sim3, env)
                    return idle_result
            else:
                return None, sim2
