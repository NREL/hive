from typing import NamedTuple, Tuple, Optional

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
        pass

    def exit(self, sim: SimulationState, env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        pass

    def _has_reached_terminal_state_condition(self, sim: SimulationState, env: Environment) -> bool:
        """
        this terminates when we reach a base
        :param sim: the sim state
        :param env: the sim environment
        :return: True if we have reached the base
        """
        return len(self.route) == 0

    def _default_terminal_state_transition(self,
                                           sim: SimulationState,
                                           env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        """
        by default, transition to idle
        :param sim: the sim state
        :param env: the sim environment
        :return:  an exception due to failure or an optional updated simulation
        """
        vehicle = sim.vehicles.get(self.vehicle_id)
        next_state = Idle(self.vehicle_id)
        return next_state.enter(sim, env)

    def _perform_update(self,
                        sim: SimulationState,
                        env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        pass