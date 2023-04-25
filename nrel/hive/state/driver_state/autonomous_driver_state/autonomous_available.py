from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Tuple, Optional, TYPE_CHECKING

from nrel.hive.dispatcher.instruction.instruction import Instruction
from nrel.hive.state.driver_state.autonomous_driver_state.autonomous_driver_attributes import (
    AutonomousDriverAttributes,
)
from nrel.hive.state.driver_state.driver_instruction_ops import (
    av_charge_base_instruction,
    av_dispatch_base_instruction,
    idle_if_at_soc_limit,
)
from nrel.hive.state.driver_state.driver_state import DriverState
from nrel.hive.state.vehicle_state.charging_station import ChargingStation
from nrel.hive.state.vehicle_state.idle import Idle
from nrel.hive.state.vehicle_state.reserve_base import ReserveBase
from nrel.hive.util import BaseId

if TYPE_CHECKING:
    from nrel.hive.state.simulation_state.simulation_state import SimulationState
    from nrel.hive.runner.environment import Environment
    from nrel.hive.util.typealiases import ScheduleId

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class AutonomousAvailable(DriverState):
    """
    an autonomous driver that is available to work
    """

    attributes: AutonomousDriverAttributes

    @property
    def schedule_id(cls) -> Optional[ScheduleId]:
        return None

    @property
    def available(cls):
        return True

    @property
    def allows_pooling(cls):
        return True

    @property
    def home_base_id(cls) -> Optional[BaseId]:
        return None

    def generate_instruction(
        self,
        sim: SimulationState,
        env: Environment,
        previous_instructions: Optional[Tuple[Instruction, ...]] = None,
    ) -> Optional[Instruction]:
        my_vehicle = sim.vehicles.get(self.attributes.vehicle_id)

        if my_vehicle is None:
            log.error(f"vehicle {self.attributes.vehicle_id} not found for driver")
            return None

        if isinstance(my_vehicle.vehicle_state, ReserveBase):
            return av_charge_base_instruction(my_vehicle, sim, env)
        elif isinstance(my_vehicle.vehicle_state, Idle):
            return av_dispatch_base_instruction(my_vehicle, sim, env)
        elif isinstance(my_vehicle.vehicle_state, ChargingStation):
            return idle_if_at_soc_limit(my_vehicle, env)
        else:
            return None

    def update(
        self, sim: SimulationState, env: Environment
    ) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        # there is no other state for an autonomous driver, so, this is a noop
        return None, sim
