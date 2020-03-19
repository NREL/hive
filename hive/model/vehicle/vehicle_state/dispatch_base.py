from typing import NamedTuple, Tuple, Optional

from hive.model.vehicle.vehicle_state import vehicle_state_ops
from hive.model.vehicle.vehicle_state.idle import Idle
from hive.model.vehicle.vehicle_state.out_of_service import OutOfService
from hive.model.vehicle.vehicle_state.reserve_base import ReserveBase
from hive.util.exception import SimulationStateError

from hive.model.roadnetwork.route import Route

from hive.util.typealiases import BaseId, VehicleId

from hive import SimulationState, Environment
from hive.model.vehicle.vehicle_state.vehicle_state import VehicleState


class DispatchBase(NamedTuple, VehicleState):
    vehicle_id: VehicleId
    base_id: BaseId
    route: Route

    def update(self, sim: SimulationState, env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        return VehicleState.default_update(sim, env, self)

    def enter(self, sim: SimulationState, env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        return VehicleState.default_enter(sim, self.vehicle_id, self)

    def exit(self, sim: SimulationState, env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        return None, sim

    def _has_reached_terminal_state_condition(self, sim: SimulationState, env: Environment) -> bool:
        """
        this terminates when we reach a base
        :param sim: the sim state
        :param env: the sim environment
        :return: True if we have reached the base
        """
        return len(self.route) == 0

    def _enter_default_terminal_state(self,
                                      sim: SimulationState,
                                      env: Environment
                                      ) -> Tuple[Optional[Exception], Optional[Tuple[SimulationState, VehicleState]]]:
        """
        by default, transition to ReserveBase if there are stalls, otherwise, Idle
        :param sim: the sim state
        :param env: the sim environment
        :return:  an exception due to failure or an optional updated simulation
        """
        vehicle = sim.vehicles.get(self.vehicle_id)
        base = sim.bases.get(self.base_id)
        if not base:
            return SimulationStateError(f"base {self.base_id} not found"), None
        elif base.geoid != vehicle.geoid:
            locations = f"{base.geoid} != {vehicle.geoid}"
            message = f"vehicle {self.vehicle_id} ended trip to base {self.base_id} but locations do not match: {locations}"
            return SimulationStateError(message), None
        else:
            next_state = ReserveBase(self.vehicle_id, self.base_id) if base.available_stalls > 0 else Idle(self.vehicle_id)
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

        move_error, move_result = vehicle_state_ops.move(sim, env, self.vehicle_id, self.route)
        moved_vehicle = move_result.sim.vehicles.get(self.vehicle_id) if move_result else None

        if move_error:
            return move_error, None
        elif not moved_vehicle:
            return SimulationStateError(f"vehicle {self.vehicle_id} not found"), None
        elif isinstance(moved_vehicle.vehicle_state, OutOfService):
            return None, move_result
        else:
            # update moved vehicle's state (holding the route)
            updated_state = self._replace(route=move_result.route_traversal.remaining_route)
            updated_vehicle = moved_vehicle.modify_state(updated_state)
            updated_sim = move_result.sim.modify_vehicle(updated_vehicle)
            return None, updated_sim
