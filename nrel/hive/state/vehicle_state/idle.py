from __future__ import annotations

import logging
from dataclasses import dataclass, replace
from typing import Tuple, Optional, TYPE_CHECKING
from uuid import uuid4

from nrel.hive.runner.environment import Environment
from nrel.hive.state.simulation_state import simulation_state_ops
from nrel.hive.state.vehicle_state.out_of_service import OutOfService
from nrel.hive.state.vehicle_state.vehicle_state import (
    VehicleState,
    VehicleStateInstanceId,
)
from nrel.hive.state.vehicle_state.vehicle_state_type import VehicleStateType
from nrel.hive.util.exception import SimulationStateError
from nrel.hive.util.typealiases import VehicleId
from nrel.hive.util.units import Seconds

if TYPE_CHECKING:
    from nrel.hive.state.simulation_state.simulation_state import SimulationState

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Idle(VehicleState):
    vehicle_id: VehicleId
    instance_id: VehicleStateInstanceId

    idle_duration: Seconds = 0

    @classmethod
    def build(cls, vehicle_id: VehicleId) -> Idle:
        return Idle(vehicle_id=vehicle_id, instance_id=uuid4())

    @property
    def vehicle_state_type(cls) -> VehicleStateType:
        return VehicleStateType.IDLE

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
        If energy has run out, we will move to OutOfService

        :param sim: the sim state
        :param env: the sim environment
        :return: True if we have run out of energy
        """
        vehicle = sim.vehicles.get(self.vehicle_id)
        if vehicle is None:
            log.error(f"vehicle {self.vehicle_id} not found in sim")
            return False

        mechatronics = env.mechatronics.get(vehicle.mechatronics_id)
        if mechatronics is None:
            log.error(f"mechatronics {vehicle.mechatronics_id} not found in sim")
            return False
        return not vehicle or mechatronics.is_empty(vehicle)

    def _default_terminal_state(
        self, sim: SimulationState, env: Environment
    ) -> Tuple[Optional[Exception], Optional[VehicleState]]:
        """
        give the default state to transition to after having met a terminal condition

        :param sim: the simulation state
        :param env: the simulation environment
        :return: an exception due to failure or the next_state after finishing a task
        """
        next_state = OutOfService.build(self.vehicle_id)
        return None, next_state

    def _perform_update(
        self, sim: SimulationState, env: Environment
    ) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        """
        incur an idling cost

        :param sim: the simulation state
        :param env: the simulation environment
        :return: the sim state with vehicle moved
        """
        vehicle = sim.vehicles.get(self.vehicle_id)
        context = f"vehicle {self.vehicle_id} idling"
        if not vehicle:
            return (
                SimulationStateError(f"vehicle not found; context: {context}"),
                None,
            )
        mechatronics = env.mechatronics.get(vehicle.mechatronics_id)

        if not mechatronics:
            return (
                SimulationStateError(f"cannot find {vehicle.mechatronics_id} in environment"),
                None,
            )
        else:
            less_energy_vehicle = mechatronics.idle(vehicle, sim.sim_timestep_duration_seconds)

            updated_idle_duration = self.idle_duration + sim.sim_timestep_duration_seconds
            updated_state = replace(self, idle_duration=updated_idle_duration)
            updated_vehicle = less_energy_vehicle.modify_vehicle_state(updated_state)

            return simulation_state_ops.modify_vehicle(sim, updated_vehicle)
