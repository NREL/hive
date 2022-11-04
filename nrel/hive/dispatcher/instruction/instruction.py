from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, TYPE_CHECKING, Tuple

import immutables

from nrel.hive.dispatcher.instruction.instruction_result import InstructionResult
from nrel.hive.util.typealiases import VehicleId

if TYPE_CHECKING:
    from nrel.hive.state.simulation_state.simulation_state import SimulationState
    from nrel.hive.runner.environment import Environment


@dataclass(frozen=True)
class InstructionMixin:
    vehicle_id: VehicleId


class InstructionABC(ABC):
    """
    an abstract base class for instructions.
    """

    @abstractmethod
    def apply_instruction(
        self, sim_state: SimulationState, env: Environment
    ) -> Tuple[Optional[Exception], Optional[InstructionResult]]:
        """
        attempts to apply an instruction to a vehicle

        :param sim_state: the state of the simulation
        :param env: the simulation environment
        :return: an exception, the resulting simulation state, or (None, None) if a bad instruction
        """
        pass


class Instruction(InstructionMixin, InstructionABC):
    """"""


InstructionMap = immutables.Map[VehicleId, Instruction]
