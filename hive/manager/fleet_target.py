from typing import NamedTuple, Dict, FrozenSet

from hive.model.vehiclestate import VehicleState

VehicleStateSet = FrozenSet[VehicleState, ...]


class FleetTarget(NamedTuple):
    n_vehicles: int
    # spatial_distribution


FleetStateTarget = Dict[VehicleStateSet, FleetTarget]
