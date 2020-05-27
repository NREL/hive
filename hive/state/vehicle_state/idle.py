from typing import NamedTuple, Tuple, Optional

from hive.runner.environment import Environment
from hive.state.simulation_state import simulation_state_ops
from hive.state.vehicle_state.vehicle_state import VehicleState
from hive.state.vehicle_state.out_of_service import OutOfService
from hive.util.exception import SimulationStateError
from hive.util.typealiases import VehicleId
from hive.util.units import Seconds


class Idle(NamedTuple, VehicleState):
    vehicle_id: VehicleId
    idle_duration: Seconds = 0

    def update(self, sim: 'SimulationState', env: Environment) -> Tuple[Optional[Exception], Optional['SimulationState']]:
        return VehicleState.default_update(sim, env, self)

    def enter(self, sim: 'SimulationState', env: Environment) -> Tuple[Optional[Exception], Optional['SimulationState']]:
        return VehicleState.apply_new_vehicle_state(sim, self.vehicle_id, self)

    def exit(self, sim: 'SimulationState', env: Environment) -> Tuple[Optional[Exception], Optional['SimulationState']]:
        return None, sim

    def _has_reached_terminal_state_condition(self, sim: 'SimulationState', env: Environment) -> bool:
        """
        If energy has run out, we will move to OutOfService
        :param sim: the sim state
        :param env: the sim environment
        :return: True if we have run out of energy
        """
        vehicle = sim.vehicles.get(self.vehicle_id)
        mechatronics = env.mechatronics.get(vehicle.mechatronics_id)
        return not vehicle or mechatronics.is_empty(vehicle)

    def _enter_default_terminal_state(self,
                                      sim: 'SimulationState',
                                      env: Environment
                                      ) -> Tuple[Optional[Exception], Optional[Tuple['SimulationState', VehicleState]]]:
        """
        Idle is the global terminal state - NOOP
        :param sim: the sim state
        :param env: the sim environment
        :return:  an exception due to failure or an optional updated simulation
        """
        next_state = OutOfService(self.vehicle_id)
        error, updated_sim = next_state.enter(sim, env)
        if error:
            return error, None
        else:
            return None, (updated_sim, next_state)

    def _perform_update(self,
                        sim: 'SimulationState',
                        env: Environment) -> Tuple[Optional[Exception], Optional['SimulationState']]:
        """
        incur an idling cost
        :param sim: the simulation state
        :param env: the simulation environment
        :return: the sim state with vehicle moved
        """
        vehicle = sim.vehicles.get(self.vehicle_id)
        mechatronics = env.mechatronics.get(vehicle.mechatronics_id)
        if not vehicle:
            return SimulationStateError(f"vehicle {self.vehicle_id} not found"), None
        elif not mechatronics:
            return SimulationStateError(f"cannot find {vehicle.mechatronics_id} in environment"), None
        else:
            less_energy_vehicle = mechatronics.idle(vehicle, sim.sim_timestep_duration_seconds)

            updated_idle_duration = (self.idle_duration + sim.sim_timestep_duration_seconds)
            updated_state = self._replace(idle_duration=updated_idle_duration)
            updated_vehicle = less_energy_vehicle.modify_state(updated_state)

            return simulation_state_ops.modify_vehicle(sim, updated_vehicle)
