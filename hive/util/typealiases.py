from typing import Tuple

# MODEL ID TYPES
RequestId = str
VehicleId = str
StationId = str
PowertrainId = str
PowercurveId = str
BaseId = str
PassengerId = str

# POSITIONAL
GeoId = str  # h3 geohash
LinkId = str # road network link
RouteStepPointer = int
H3Line = Tuple[GeoId, ...]

SimTime = int



