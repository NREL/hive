# from __future__ import annotations
#
# from enum import Enum
#
#
# class VehicleState(Enum):
#     """
#     A finite set of vehicle states and rules for state transitions
#     """
#
#     # INACTIVE FLEET MANAGEMENT
#     DISPATCH_BASE = 0
#     RESERVE_BASE = 1
#     # ACTIVE FLEET MANAGEMENT
#     IDLE = 2
#     REPOSITIONING = 3
#     # TRIPPING
#     DISPATCH_TRIP = 4
#     SERVICING_TRIP = 5
#     # CHARGING
#     DISPATCH_STATION = 6
#     CHARGING = 7
#     # MISC
#     OUT_OF_SERVICE = 8
#
#     @classmethod
#     def is_valid(cls, state) -> bool:
#         """
#         Determines if a state is valid
#
#         :param state: vehicle state
#         :return: Boolean
#         """
#         return state in _VALID_VEHICLE_STATES
#
#
# _VALID_VEHICLE_STATES = frozenset([
#     VehicleState.DISPATCH_BASE,
#     VehicleState.RESERVE_BASE,
#     VehicleState.IDLE,
#     VehicleState.DISPATCH_TRIP,
#     VehicleState.DISPATCH_STATION,
#     VehicleState.CHARGING,
#     VehicleState.REPOSITIONING,
#     VehicleState.SERVICING_TRIP,
#     VehicleState.OUT_OF_SERVICE
# ])
#
#
# class VehicleStateCategory(Enum):
#     """
#     higher-order categories for vehicle state
#     """
#     DO_NOTHING = 0
#     CHARGE = 1
#     MOVE = 2
#
#     @classmethod
#     def from_vehicle_state(cls, vehicle_state: VehicleState) -> VehicleStateCategory:
#         """
#         maps a VehicleStateCategory from a VehicleState.
#
#         :param vehicle_state: the vehicle state
#         :return: the vehicle state category
#         """
#         return _VEHICLE_STATE_CATEGORY[vehicle_state]
#
#
# _VEHICLE_STATE_CATEGORY = {
#     VehicleState.DISPATCH_BASE: VehicleStateCategory.MOVE,
#     VehicleState.CHARGING: VehicleStateCategory.CHARGE,
#     VehicleState.RESERVE_BASE: VehicleStateCategory.DO_NOTHING,
#     VehicleState.IDLE: VehicleStateCategory.DO_NOTHING,
#     VehicleState.REPOSITIONING: VehicleStateCategory.MOVE,
#     VehicleState.DISPATCH_TRIP: VehicleStateCategory.MOVE,
#     VehicleState.SERVICING_TRIP: VehicleStateCategory.MOVE,
#     VehicleState.DISPATCH_STATION: VehicleStateCategory.MOVE,
#     VehicleState.CHARGING: VehicleStateCategory.CHARGE,
#     VehicleState.OUT_OF_SERVICE: VehicleStateCategory.DO_NOTHING
# }
