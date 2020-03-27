from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING

from hive.util.abc_named_tuple_meta import ABCNamedTupleMeta

if TYPE_CHECKING:
    from hive.dispatcher.instruction.instruction_interface import InstructionMap
    from hive.state.simulation_state.simulation_state import SimulationState


class FleetTarget(metaclass=ABCNamedTupleMeta):
    """
    an abstract base class for fleet targets.
    """

    @abstractmethod
    def apply_target(self, sim_state: SimulationState,) -> InstructionMap:
        """
        generates dispatcher instructions based on a specific simulation state

        :param sim_state: the state of the simulation

        :return: a set of instructions mapped to a specific vehicle
        """
        pass
