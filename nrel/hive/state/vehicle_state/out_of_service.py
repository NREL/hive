from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple, Optional, TYPE_CHECKING
from uuid import uuid4

from nrel.hive.runner.environment import Environment
from nrel.hive.state.vehicle_state.vehicle_state import (
    VehicleState,
    VehicleStateInstanceId,
)
from nrel.hive.state.vehicle_state.vehicle_state_type import VehicleStateType
from nrel.hive.util.typealiases import VehicleId

if TYPE_CHECKING:
    from nrel.hive.state.simulation_state.simulation_state import SimulationState


@dataclass(frozen=True)
class OutOfService(VehicleState):
    vehicle_id: VehicleId

    instance_id: VehicleStateInstanceId

    @classmethod
    def build(cls, vehicle_id: VehicleId) -> OutOfService:
        """
        build an OutOfService state

        :param vehicle_id: the vehicle id
        :return: an OutOfService state
        """
        return cls(vehicle_id=vehicle_id, instance_id=uuid4())

    @property
    def vehicle_state_type(cls) -> VehicleStateType:
        return VehicleStateType.OUT_OF_SERVICE

    def update(
        self, sim: SimulationState, env: Environment
    ) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        return VehicleState.default_update(sim, env, self)

    def enter(
        self, sim: SimulationState, env: Environment
    ) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        new_state = VehicleState.apply_new_vehicle_state(sim, self.vehicle_id, self)
        return new_state

    def exit(
        self, next_state: VehicleState, sim: SimulationState, env: Environment
    ) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        return None, sim

    def _has_reached_terminal_state_condition(self, sim: SimulationState, env: Environment) -> bool:
        """
        There is no terminal state for OutOfService

        :param sim: the sim state
        :param env: the sim environment
        :return: False
        """
        return False

    def _default_terminal_state(
        self, sim: SimulationState, env: Environment
    ) -> Tuple[Optional[Exception], Optional[VehicleState]]:
        """
        give the default state to transition to after having met a terminal condition

        :param sim: the simulation state
        :param env: the simulation environment
        :return: an exception due to failure or the next_state after finishing a task
        """
        return None, self

    def _perform_update(
        self, sim: SimulationState, env: Environment
    ) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        """
        as of now, there is no update for being OutOfService

        :param sim: the simulation state
        :param env: the simulation environment
        :return: NOOP
        """
        return None, sim
