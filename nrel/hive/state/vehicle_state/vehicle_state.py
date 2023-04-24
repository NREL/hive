from __future__ import annotations

import logging
from abc import abstractmethod, ABC
from dataclasses import dataclass
from typing import Tuple, Optional, TYPE_CHECKING
from uuid import UUID

from nrel.hive.state.entity_state import entity_state_ops
from nrel.hive.state.simulation_state import simulation_state_ops
from nrel.hive.state.vehicle_state.vehicle_state_type import VehicleStateType
from nrel.hive.util.exception import SimulationStateError, StateTransitionError
from nrel.hive.util.typealiases import VehicleId

if TYPE_CHECKING:
    from nrel.hive.runner.environment import Environment
    from nrel.hive.state.simulation_state.simulation_state import SimulationState

log = logging.getLogger(__name__)

VehicleStateInstanceId = UUID


@dataclass(frozen=True)
class Mixin:
    vehicle_id: VehicleId
    instance_id: VehicleStateInstanceId


class VehicleStateABC(ABC):
    """
    a state representation along with methods for state transitions and discrete time step updates

    code interacting with a vehicle's state should not explicitly modify the Vehicle.vehicle_state
    and should instead call the methods enter, update, and exit.

    an enter or exit can return an exception, a SimulationState, or (None, None) signifying that the
    state cannot be entered/exited under this circumstance.
    """

    @property
    @abstractmethod
    def vehicle_state_type(cls) -> VehicleStateType:
        """
        unique state type, used for comparison, replaces need to call isinstance on the concrete
        VehicleState type (which leads to circular dependencies amongst VehicleStates)
        :return: the VehicleStateType of this VehicleState
        """
        pass

    def __repr__(self) -> str:
        return super().__repr__()

    @classmethod
    def default_update(
        mcs, sim: SimulationState, env: Environment, state: VehicleState
    ) -> Tuple[Optional[Exception], Optional[SimulationState]]:
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
            # get the default terminal state to transition into
            err1, next_state = state._default_terminal_state(sim, env)
            if err1 is not None:
                state_type = state.vehicle_state_type
                log.error(err1)
                err_res = SimulationStateError(
                    f"failure during default update of {state_type} state"
                )
                err_res.__cause__ = err1
                return err_res, None
            elif next_state is None:
                return None, None
            else:
                # perform default state transition
                (
                    err2,
                    updated_sim,
                ) = entity_state_ops.transition_previous_to_next(sim, env, state, next_state)
                if err2 is not None:
                    log.error(err2)
                    state_type = state.vehicle_state_type
                    err_res = SimulationStateError(
                        f"failure during default update of {state_type} state"
                    )
                    err_res.__cause__ = err2
                    return err_res, None
                elif updated_sim is None:
                    return None, None
                else:
                    # perform regular update function for subsequent state
                    updated_vehicle = updated_sim.vehicles.get(next_state.vehicle_id)
                    if updated_vehicle is None:
                        state_type = state.vehicle_state_type
                        err_res = SimulationStateError(
                            f"cannot find vehicle in sim after transition to {state_type} state"
                        )
                        return err_res, None
                    else:
                        updated_next_state = updated_vehicle.vehicle_state
                        return updated_next_state._perform_update(updated_sim, env)
        else:
            return state._perform_update(sim, env)

    @classmethod
    def apply_new_vehicle_state(
        mcs,
        sim: SimulationState,
        vehicle_id: VehicleId,
        new_state: VehicleState,
    ) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        """
        this default enter operation simply modifies the vehicle's stored state value

        :param sim: the simulation state
        :param vehicle_id: the id of the vehicle to transition
        :param new_state: the state we are applying
        :return: an exception due to failure or an optional updated simulation
        """
        vehicle = sim.vehicles.get(vehicle_id)
        if not vehicle:
            state_name = new_state.__class__.__name__
            error = StateTransitionError(
                f"failed to apply state {state_name}; vehicle {vehicle_id} not found"
            )
            return error, None
        else:
            updated_vehicle = vehicle.modify_vehicle_state(new_state)
            return simulation_state_ops.modify_vehicle(sim, updated_vehicle)

    @abstractmethod
    def _has_reached_terminal_state_condition(self, sim: SimulationState, env: Environment) -> bool:
        """
        test if we have reached a terminal state and need to apply the default transition

        :param sim: the simulation state
        :param env: the simulation environment
        :return: True if the termination condition has been met
        """
        pass

    @abstractmethod
    def _default_terminal_state(
        self, sim: SimulationState, env: Environment
    ) -> Tuple[Optional[Exception], Optional[VehicleState]]:
        """
        give the default state to transition to after having met a terminal condition

        :param sim: the simulation state
        :param env: the simulation environment
        :return: an exception due to failure or the next_state after finishing a task
        """
        pass

    @abstractmethod
    def _perform_update(
        self, sim: SimulationState, env: Environment
    ) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        """
        perform a simulation state update for a vehicle in this state

        :param sim: the simulation state
        :param env: the simulation environment
        :return: an exception due to failure or an optional updated simulation
        """
        pass

    @abstractmethod
    def update(
        self,
        sim: SimulationState,
        env: Environment,
    ) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        """
        apply any effects due to an entity being advanced one discrete time unit in this EntityState

        :param sim: the simulation state
        :param env: the simulation environment
        :return: an exception due to failure or an optional updated simulation
        """
        pass

    @abstractmethod
    def enter(
        self, sim: SimulationState, env: Environment
    ) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        """
        apply any effects due to an entity transitioning into this state

        :param sim: the simulation state
        :param env: the simulation environment
        :return: an exception due to failure or an optional updated simulation, or (None, None) if invalid
        """
        pass

    @abstractmethod
    def exit(
        self,
        next_state: VehicleState,
        sim: SimulationState,
        env: Environment,
    ) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        """
        apply any effects due to an entity transitioning out of this state

        :param next_state the EntityState to transition to
        :param sim: the simulation state
        :param env: the simulation environment
        :return: an exception due to failure or an optional updated simulation, or (None, None) if invalid
        """
        pass


class VehicleState(Mixin, VehicleStateABC):
    """ """
