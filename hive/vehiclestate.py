from enum import Enum
from collections import namedtuple
from hive.exception import StateTransitionError

# id used to enforce uniqueness in Python (otherwise, IDLE == REPOSITIONING, etc)
VehicleStateAttributes = namedtuple('VehStateAttributes', ['id', 'active', 'available'])


class VehicleState(Enum):
    """
    A finite set of vehicle states and rules for state transitions


    """

    # INACTIVE FLEET MANAGEMENT
    DISPATCH_BASE = VehicleStateAttributes(id=0, active=False, available=False)
    CHARGING_BASE = VehicleStateAttributes(id=1, active=False, available=False)
    RESERVE_BASE = VehicleStateAttributes(id=2, active=False, available=False)
    # ACTIVE FLEET MANAGEMENT
    IDLE = VehicleStateAttributes(id=3, active=True, available=True)
    REPOSITIONING = VehicleStateAttributes(id=4, active=True, available=True)
    # TRIPPING
    DISPATCH_TRIP = VehicleStateAttributes(id=5, active=True, available=True)
    SERVING_TRIP = VehicleStateAttributes(id=6, active=True, available=False)
    # CHARGING
    DISPATCH_STATION = VehicleStateAttributes(id=7, active=True, available=True)
    CHARGING_STATION = VehicleStateAttributes(id=8, active=True, available=False)

    def __init__(self, state_id, active, available):
        self.id = state_id
        self.active = active
        self.available = available

    def to(self, next_state):
        """
        enforces use of valid state transitions for vehicles

        @returns nextState if transition is valid

        @throws StateTransitionError
        """

        if next_state not in valid_vehicle_transitions[self]:
            raise StateTransitionError("vehicle", self.name, next_state.name)

        return next_state

    @classmethod
    def is_valid(cls, state):
        return state in valid_vehicle_states


valid_vehicle_states = frozenset([
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

valid_vehicle_transitions = {
    # INACTIVE FLEET MANAGEMENT
    VehicleState.DISPATCH_BASE: frozenset([VehicleState.CHARGING_BASE, VehicleState.RESERVE_BASE, VehicleState.IDLE]),
    VehicleState.CHARGING_BASE: frozenset([VehicleState.RESERVE_BASE, VehicleState.IDLE]),
    VehicleState.RESERVE_BASE: frozenset([VehicleState.CHARGING_BASE, VehicleState.IDLE]),
    # ACTIVE FLEET MANAGEMENT
    VehicleState.IDLE: frozenset([VehicleState.DISPATCH_BASE, VehicleState.DISPATCH_STATION,
                                  VehicleState.CHARGING_STATION, VehicleState.DISPATCH_TRIP,
                                  VehicleState.SERVING_TRIP, VehicleState.REPOSITIONING]),
    VehicleState.REPOSITIONING: frozenset([VehicleState.DISPATCH_BASE, VehicleState.DISPATCH_STATION,
                                           VehicleState.DISPATCH_TRIP, VehicleState.SERVING_TRIP, VehicleState.IDLE]),
    # TRIPPING
    VehicleState.DISPATCH_TRIP: frozenset([VehicleState.IDLE, VehicleState.SERVING_TRIP, VehicleState.DISPATCH_STATION]),
    VehicleState.SERVING_TRIP: frozenset([VehicleState.IDLE]),
    # CHARGING
    VehicleState.DISPATCH_STATION: frozenset([VehicleState.IDLE, VehicleState.CHARGING_STATION,
                                              VehicleState.DISPATCH_TRIP]),
    VehicleState.CHARGING_STATION: frozenset([VehicleState.IDLE, VehicleState.RESERVE_BASE]),
}
