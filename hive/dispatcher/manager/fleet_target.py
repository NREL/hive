from typing import NamedTuple, FrozenSet

import immutables
from hive.state.vehicle_state import VehicleState

VehicleStateSet = FrozenSet[VehicleState]

# TODO: Should StateTargetId be an enum or should we let it be flexible?
StateTargetId = str


class StateTarget(NamedTuple):
    id: StateTargetId
    state_set: VehicleStateSet
    n_vehicles: int
    # spatial_distribution


FleetStateTarget = immutables.Map[StateTargetId, StateTarget]
