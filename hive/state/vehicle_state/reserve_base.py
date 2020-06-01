from typing import NamedTuple, Tuple, Optional

from hive.runner.environment import Environment
from hive.state.simulation_state import simulation_state_ops
from hive.state.vehicle_state.vehicle_state import VehicleState
from hive.util.exception import SimulationStateError
from hive.util.typealiases import VehicleId, BaseId


class ReserveBase(NamedTuple, VehicleState):
    vehicle_id: VehicleId
    base_id: BaseId

    def update(self, sim: 'SimulationState', env: Environment) -> Tuple[Optional[Exception], Optional['SimulationState']]:
        return VehicleState.default_update(sim, env, self)

    def enter(self, sim: 'SimulationState', env: Environment) -> Tuple[Optional[Exception], Optional['SimulationState']]:
        """
        to enter this state, the base must have a stall for the vehicle
        :param sim: the sim state
        :param env: the sim environment
        :return: an exception, an updated 'SimulationState', or (None, None) when the base has no stalls
        """
        vehicle = sim.vehicles.get(self.vehicle_id)
        base = sim.bases.get(self.base_id)
        if not vehicle:
            return SimulationStateError(f"vehicle {self.vehicle_id} not found"), None
        elif not base:
            return SimulationStateError(f"base {self.base_id} not found"), None
        elif base.geoid != vehicle.geoid:
            return None, None
        else:
            updated_base = base.checkout_stall()
            if not updated_base:
                return None, None
            else:
                error, updated_sim = simulation_state_ops.modify_base(sim, updated_base)
                if error:
                    return error, None
                else:
                    return VehicleState.apply_new_vehicle_state(updated_sim, self.vehicle_id, self)

    def exit(self, sim: 'SimulationState', env: Environment) -> Tuple[Optional[Exception], Optional['SimulationState']]:
        """
        releases the stall that this vehicle occupied
        :param sim: the sim state
        :param env: the sim environment
        :return: an exception, or an updated sim
        """
        base = sim.bases.get(self.base_id)
        if not base:
            return SimulationStateError(f"base {self.base_id} not found"), None
        else:
            updated_base = base.return_stall()
            return simulation_state_ops.modify_base(sim, updated_base)

    def _has_reached_terminal_state_condition(self, sim: 'SimulationState', env: Environment) -> bool:
        """
        There is no terminal state for ReserveBase
        :param sim: the sim state
        :param env: the sim environment
        :return: False
        """
        return False

    def _enter_default_terminal_state(self,
                                      sim: 'SimulationState',
                                      env: Environment
                                      ) -> Tuple[Optional[Exception], Optional[Tuple['SimulationState', VehicleState]]]:
        """
        There is no terminal state for ReserveBase
        :param sim: the sim state
        :param env: the sim environment
        :return:  an exception due to failure or an optional updated simulation
        """
        return None, (sim, self)

    def _perform_update(self,
                        sim: 'SimulationState',
                        env: Environment) -> Tuple[Optional[Exception], Optional['SimulationState']]:
        """
        as of now, there is no update for being ReserveBase
        :param sim: the simulation state
        :param env: the simulation environment
        :return: NOOP
        """
        return None, sim
