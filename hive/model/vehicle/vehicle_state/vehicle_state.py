from __future__ import annotations

from abc import abstractmethod, ABCMeta
from typing import Tuple, Optional, NamedTupleMeta

from hive.util.typealiases import VehicleId

from hive.util.exception import SimulationStateError

from hive.state.entity_state import EntityState

from hive.runner.environment import Environment
from hive.state.simulation_state import SimulationState


class VehicleState(ABCMeta, NamedTupleMeta, EntityState):
    """
    a state representation along with methods for state transitions and discrete time step updates

    code interacting with a vehicle's state should not explicitly modify the Vehicle.vehicle_state
    and should instead call the methods enter, update, and exit.
    """

    @classmethod
    def default_update(mcs,
                       sim: SimulationState,
                       env: Environment,
                       state: VehicleState) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        """
        apply any effects due to a vehicle being advanced one discrete time unit in this VehicleState.
        under terminal conditions, exits the current state, enters a default transition state, and steps
        under the condition of that state.
        :param sim: the simulation state
        :param env: the simulation environment
        :param state: the vehicle state we are updating
        :return: an exception due to failure or an optional updated simulation
        """
        terminal_state_condition_met = state._has_reached_terminal_state_condition(sim, env)
        if terminal_state_condition_met:
            exit_error, exited_sim = state.exit(sim, env)
            if exit_error:
                return exit_error, None
            else:
                next_error, (next_sim, next_state) = state._enter_default_terminal_state(exited_sim, env)
                if next_error:
                    return next_error, None
                else:
                    # apply the update of the next state
                    return next_state.update(next_sim, env)

        else:
            return state._perform_update(sim, env)

    @classmethod
    def default_enter(mcs,
                      sim: SimulationState,
                      vehicle_id: VehicleId,
                      new_state: VehicleState
                      ) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        """
        the default enter operation simply modifies the vehicle's stored state value
        :param sim: the simulation state
        :param vehicle_id: the id of the vehicle to transition
        :param new_state: the state we are applying
        :return: an exception due to failure or an optional updated simulation
        """
        vehicle = sim.vehicles.get(vehicle_id)
        if not vehicle:
            return SimulationStateError(f"vehicle {vehicle_id} not found"), None
        else:
            updated_vehicle = vehicle.modify_state(new_state)
            updated_sim = sim.modify_vehicle(updated_vehicle)
            return None, updated_sim

    @abstractmethod
    def _has_reached_terminal_state_condition(self,
                                              sim: SimulationState,
                                              env: Environment) -> bool:
        """
        test if we have reached a terminal state and need to apply the default transition
        :param sim: the simulation state
        :param env: the simulation environment
        :return: True if the termination condition has been met
        """
        pass

    @abstractmethod
    def _enter_default_terminal_state(self,
                                      sim: SimulationState,
                                      env: Environment
                                      ) -> Tuple[Optional[Exception], Optional[Tuple[SimulationState, VehicleState]]]:
        """
        apply a transition to a default state after having met a terminal condition
        :param sim: the simulation state
        :param env: the simulation environment
        :return: an exception due to failure or an optional updated simulation
        """
        pass

    @abstractmethod
    def _perform_update(self,
                        sim: SimulationState,
                        env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        """
        perform a simulation state update for a vehicle in this state
        :param sim: the simulation state
        :param env: the simulation environment
        :return: an exception due to failure or an optional updated simulation
        """
        pass
