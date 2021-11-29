from typing import Tuple, FrozenSet, Callable, TypeVar

from immutables import Map

# MODEL ID TYPES
RequestId = str
VehicleId = str
StationId = str
PowertrainId = str
PowercurveId = str
BaseId = str
PassengerId = str
VehicleTypeId = str
MechatronicsId = str
ChargerId = str
ScheduleId = str
MembershipId = str

Entity = TypeVar('Entity')
EntityId = TypeVar('EntityId')

# Collections
MembershipMap = Map[EntityId, Tuple[MembershipId, ...]]

# POSITIONAL
GeoId = str  # h3 geohash
LinkId = str  # road network link
RouteStepPointer = int
H3Resolution = int
H3Line = Tuple[GeoId, ...]
GeoFenceSet = FrozenSet[GeoId]

SimStep = int  # the iteration of the simulation

# FUNCTIONS

# if we create a DriverId type, and it has a lookup table on SimulationState, we may
# want to change this from VehicleId to DriverId
ScheduleFunction = Callable[['SimulationState', VehicleId], bool]
