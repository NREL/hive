from __future__ import annotations
from typing import NamedTuple, TYPE_CHECKING

if TYPE_CHECKING:
    from hive.state.vehicle_state.vehicle_state import VehicleState


class InstructionResult(NamedTuple):
    prev_state: VehicleState
    next_state: VehicleState
