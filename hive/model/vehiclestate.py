from __future__ import annotations

from enum import Enum

class VehicleState(Enum):
    """
    A finite set of vehicle states and rules for state transitions


    """

    # INACTIVE FLEET MANAGEMENT
    DISPATCH_BASE = 0
    CHARGING_BASE = 1
    RESERVE_BASE = 2
    # ACTIVE FLEET MANAGEMENT
    IDLE = 3
    REPOSITIONING = 4
    # TRIPPING
    DISPATCH_TRIP = 5
    SERVICING_TRIP = 6
    # CHARGING
    DISPATCH_STATION = 7
    CHARGING_STATION = 8

    def active(self):
        return _state_active_properties[self]

    def available(self):
        return _state_available_properties[self]

    @classmethod
    def is_valid(cls, state):
        return state in _valid_vehicle_states


_state_active_properties = {
    VehicleState.DISPATCH_BASE: False,
    VehicleState.CHARGING_BASE: False,
    VehicleState.RESERVE_BASE: False,
    VehicleState.IDLE: True,
    VehicleState.REPOSITIONING: True,
    VehicleState.DISPATCH_TRIP: True,
    VehicleState.SERVICING_TRIP: True,
    VehicleState.DISPATCH_STATION: True,
    VehicleState.CHARGING_STATION: True
}

_state_available_properties = {
    VehicleState.DISPATCH_BASE: False,
    VehicleState.CHARGING_BASE: False,
    VehicleState.RESERVE_BASE: False,
    VehicleState.IDLE: True,
    VehicleState.REPOSITIONING: True,
    VehicleState.DISPATCH_TRIP: False,
    VehicleState.SERVICING_TRIP: False,
    VehicleState.DISPATCH_STATION: False,
    VehicleState.CHARGING_STATION: False
}

_valid_vehicle_states = frozenset([
    VehicleState.DISPATCH_BASE,
    VehicleState.CHARGING_BASE,
    VehicleState.RESERVE_BASE,
    VehicleState.IDLE,
    VehicleState.DISPATCH_TRIP,
    VehicleState.DISPATCH_STATION,
    VehicleState.CHARGING_STATION,
    VehicleState.REPOSITIONING,
    VehicleState.SERVICING_TRIP
])


class VehicleStateCategory(Enum):
    """
    higher-order categories for vehicle state
    """
    DO_NOTHING = 0
    CHARGE = 1
    MOVE = 2

    @classmethod
    def from_vehicle_state(cls, vehicle_state: VehicleState) -> VehicleStateCategory:
        return _vehicle_state_category[vehicle_state]


_vehicle_state_category = {
    VehicleState.DISPATCH_BASE: VehicleStateCategory.MOVE,
    VehicleState.CHARGING_BASE: VehicleStateCategory.CHARGE,
    VehicleState.RESERVE_BASE: VehicleStateCategory.DO_NOTHING,
    VehicleState.IDLE: VehicleStateCategory.DO_NOTHING,
    VehicleState.REPOSITIONING: VehicleStateCategory.MOVE,
    VehicleState.DISPATCH_TRIP: VehicleStateCategory.MOVE,
    VehicleState.SERVICING_TRIP: VehicleStateCategory.MOVE,
    VehicleState.DISPATCH_STATION: VehicleStateCategory.MOVE,
    VehicleState.CHARGING_STATION: VehicleStateCategory.CHARGE
}