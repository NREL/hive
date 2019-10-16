from enum import Enum
from hive.exception import StateTransitionError


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
    SERVING_TRIP = 6
    # CHARGING
    DISPATCH_STATION = 7
    CHARGING_STATION = 8

    def to(self, next_state):
        """
        enforces use of valid state transitions for vehicles

        @returns id of next_state if transition is valid

        @throws StateTransitionError
        """

        if next_state not in _valid_vehicle_transitions[self]:
            raise StateTransitionError("vehicle", self.name, next_state.name)

        return next_state

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
    VehicleState.SERVING_TRIP: True,
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
    VehicleState.SERVING_TRIP: False,
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
    VehicleState.SERVING_TRIP
])

# TODO: some state transitions listed below are not consistent with Vehicle FSM illustration but added
#  in order to work with current version of HIVE (labeled below "NOT IN FSM")
_valid_vehicle_transitions = {
    # INACTIVE FLEET MANAGEMENT
    VehicleState.DISPATCH_BASE: frozenset([
        VehicleState.CHARGING_BASE,
        VehicleState.RESERVE_BASE,
        VehicleState.IDLE  # NOT IN FSM
    ]),

    VehicleState.CHARGING_BASE: frozenset([
        VehicleState.RESERVE_BASE,
        VehicleState.IDLE
    ]),

    VehicleState.RESERVE_BASE: frozenset([
        VehicleState.CHARGING_BASE,
        VehicleState.IDLE
    ]),

    # ACTIVE FLEET MANAGEMENT
    VehicleState.IDLE: frozenset([
        VehicleState.DISPATCH_BASE,
        VehicleState.DISPATCH_STATION,
        VehicleState.CHARGING_STATION,  # NOT IN FSM
        VehicleState.DISPATCH_TRIP,
        VehicleState.SERVING_TRIP,
        VehicleState.REPOSITIONING,
        VehicleState.CHARGING_BASE  # NOT IN FSM
    ]),

    VehicleState.REPOSITIONING: frozenset([
        VehicleState.DISPATCH_BASE,
        VehicleState.DISPATCH_STATION,
        VehicleState.DISPATCH_TRIP,
        VehicleState.SERVING_TRIP,
        VehicleState.IDLE
    ]),

    # TRIPPING
    VehicleState.DISPATCH_TRIP: frozenset([
        VehicleState.IDLE,
        VehicleState.SERVING_TRIP,
        VehicleState.DISPATCH_STATION  # NOT IN FSM
    ]),

    VehicleState.SERVING_TRIP: frozenset([
        VehicleState.IDLE
    ]),

    # CHARGING
    VehicleState.DISPATCH_STATION: frozenset([
        VehicleState.IDLE,
        VehicleState.CHARGING_STATION,
        VehicleState.DISPATCH_TRIP  # NOT IN FSM
    ]),

    VehicleState.CHARGING_STATION: frozenset([
        VehicleState.IDLE,
        VehicleState.RESERVE_BASE  # NOT IN FSM
    ]),
}
