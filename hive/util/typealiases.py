from typing import Tuple, FrozenSet, Callable

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

# POSITIONAL
GeoId = str  # h3 geohash
LinkId = str # road network link
RouteStepPointer = int
H3Resolution = int
H3Line = Tuple[GeoId, ...]
GeoFenceSet = FrozenSet[GeoId]

SimTime = int  # time in seconds consistent across inputs (epoch time preferred)
SimStep = int  # the iteration of the simulation

# FUNCTIONS

# if we create a DriverId type, and it has a lookup table on SimulationState, we may
# want to change this from VehicleId to DriverId
ScheduleFunction = Callable[['SimulationState', VehicleId], bool]
