from typing import NamedTuple, Tuple, Optional

from hive import SimulationState, Environment
from hive.model.vehicle.vehicle_state.vehicle_state import VehicleState
from hive.util.typealiases import VehicleId


class OutOfService(NamedTuple, VehicleState):
    vehicle_id: VehicleId

    def update(self, sim: SimulationState, env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        return VehicleState.default_update(sim, env, self)

    def enter(self, sim: SimulationState, env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        return VehicleState.default_enter(sim, self.vehicle_id, self)

    def exit(self, sim: SimulationState, env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        return None, sim

    def _has_reached_terminal_state_condition(self, sim: SimulationState, env: Environment) -> bool:
        """
        There is no terminal state for OutOfService
        :param sim: the sim state
        :param env: the sim environment
        :return: False
        """
        return False

    def _enter_default_terminal_state(self,
                                      sim: SimulationState,
                                      env: Environment
                                      ) -> Tuple[Optional[Exception], Optional[Tuple[SimulationState, VehicleState]]]:
        """
        There is no terminal state for OutOfService
        :param sim: the sim state
        :param env: the sim environment
        :return:  an exception due to failure or an optional updated simulation
        """
        return None, (sim, self)

    def _perform_update(self,
                        sim: SimulationState,
                        env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        """
        as of now, there is no update for being OutOfService
        :param sim: the simulation state
        :param env: the simulation environment
        :return: NOOP
        """
        return None, sim
