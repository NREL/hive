from __future__ import annotations

from abc import abstractmethod
from typing import Optional, TYPE_CHECKING

from hive.util.abc_named_tuple_meta import ABCNamedTupleMeta
if TYPE_CHECKING:
    from hive.state.simulation_state import SimulationState


class Instruction(metaclass=ABCNamedTupleMeta):
    """
    an abstract base class for instructions.
    """

    @abstractmethod
    def apply_instruction(self, sim_state: SimulationState) -> Optional[SimulationState]:
        pass
