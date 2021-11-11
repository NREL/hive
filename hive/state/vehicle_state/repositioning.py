from typing import NamedTuple, Tuple, Optional

from hive.model.roadnetwork.route import Route, route_cooresponds_with_entities
from hive.runner.environment import Environment
from hive.state.simulation_state import simulation_state_ops
from hive.state.vehicle_state import vehicle_state_ops
from hive.state.vehicle_state.idle import Idle
from hive.state.vehicle_state.vehicle_state import VehicleState
from hive.state.vehicle_state.vehicle_state_type import VehicleStateType
from hive.util.exception import SimulationStateError
from hive.util.typealiases import VehicleId


class Repositioning(NamedTuple, VehicleState):
    vehicle_id: VehicleId
    route: Route

    @property
    def vehicle_state_type(cls) -> VehicleStateType:
        return VehicleStateType.REPOSITIONING

    def update(self, sim: 'SimulationState', env: Environment) -> Tuple[Optional[Exception], Optional['SimulationState']]:
        return VehicleState.default_update(sim, env, self)

    def enter(self, sim: 'SimulationState', env: Environment) -> Tuple[Optional[Exception], Optional['SimulationState']]:
        vehicle = sim.vehicles.get(self.vehicle_id)
        is_valid = route_cooresponds_with_entities(self.route, vehicle.position) if vehicle else False
        context = f"vehicle {self.vehicle_id} entering repositioning state"
        if not vehicle:
            return SimulationStateError(f"vehicle not found; context: {context}"), None
        elif not is_valid:
            return None, None
        else:
            result = VehicleState.apply_new_vehicle_state(sim, self.vehicle_id, self)
            return result

    def exit(self, sim: 'SimulationState', env: Environment) -> Tuple[Optional[Exception], Optional['SimulationState']]:
        return None, sim

    def _has_reached_terminal_state_condition(self, sim: 'SimulationState', env: Environment) -> bool:
        """
        this terminates when we reach a base

        :param sim: the sim state
        :param env: the sim environment
        :return: True if we have reached the base
        """
        return len(self.route) == 0

    def _enter_default_terminal_state(self,
                                      sim: 'SimulationState',
                                      env: Environment
                                      ) -> Tuple[Optional[Exception], Optional[Tuple['SimulationState', VehicleState]]]:
        """
        by default, transition to ReserveBase if there are stalls, otherwise, Idle

        :param sim: the sim state
        :param env: the sim environment
        :return:  an exception due to failure or an optional updated simulation
        """
        next_state = Idle(self.vehicle_id)
        enter_error, enter_sim = next_state.enter(sim, env)
        if enter_error:
            return enter_error, None
        else:
            return None, (enter_sim, next_state)

    def _perform_update(self,
                        sim: 'SimulationState',
                        env: Environment) -> Tuple[Optional[Exception], Optional['SimulationState']]:
        """
        take a step along the route to the base

        :param sim: the simulation state
        :param env: the simulation environment
        :return: the sim state with vehicle moved
        """

        move_error, move_result = vehicle_state_ops.move(sim, env, self.vehicle_id, self.route)
        moved_vehicle = move_result.sim.vehicles.get(self.vehicle_id) if move_result else None

        context = f"vehicle {self.vehicle_id} performing update in repositioning state"
        if move_error:
            return move_error, None
        elif not moved_vehicle:
            return SimulationStateError(f"vehicle {self.vehicle_id} not found; context: {context}"), None
        elif moved_vehicle.vehicle_state.vehicle_state_type == VehicleStateType.OUT_OF_SERVICE:
            return None, move_result.sim
        else:
            # update moved vehicle's state (holding the route)
            updated_state = self._replace(route=move_result.route_traversal.remaining_route)
            updated_vehicle = moved_vehicle.modify_vehicle_state(updated_state)
            return simulation_state_ops.modify_vehicle(sim, updated_vehicle)
