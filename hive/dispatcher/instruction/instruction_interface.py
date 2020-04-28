from __future__ import annotations

from abc import abstractmethod
from typing import Optional, TYPE_CHECKING, Tuple

import immutables

from hive.util.abc_named_tuple_meta import ABCNamedTupleMeta
from hive.util.typealiases import VehicleId

if TYPE_CHECKING:
    from hive.state.simulation_state.simulation_state import SimulationState
    from hive.runner.environment import Environment


class Instruction(metaclass=ABCNamedTupleMeta):
    """
    an abstract base class for instructions.
    """

    @abstractmethod
    def prepare_instruction(self,
                            sim_state: SimulationState,
                            env: Environment) -> Tuple[Optional[Exception], Optional[Instruction]]:
        """
        performs any work needed to apply the instruction which does not modify the Sim, such as routing
        :return: the prepared instruction, or an exception
        """
        pass

    @abstractmethod
    def apply_instruction(self,
                          sim_state: SimulationState,
                          env: Environment) -> Tuple[Optional[Exception], Optional[SimulationState]]:
        """
        attempts to apply an instruction to a vehicle

        :param sim_state: the state of the simulation
        :param env: the simulation environment

        :return: an exception, the resulting simulation state, or (None, None) if a bad instruction
        """
        pass

    @property
    @abstractmethod
    def vehicle_id(self) -> VehicleId:
        """
        the id of the vehicle to apply this instruction to

        :return:
        """
        pass


InstructionMap = immutables.Map[VehicleId, Instruction]
