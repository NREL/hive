from typing import Tuple

# MODEL ID TYPES
RequestId = str
VehicleId = str
StationId = str
PowertrainId = str
BaseId = str
PassengerId = str

# POSITIONAL
GeoId = str  # h3 geohash
LinkId = str # road network link
RouteStepPointer = int
H3Line = Tuple[GeoId, ...]

# NUMERICAL TYPES
# todo: Pints library!
KwH = float
Km = float
Percentage = float
Speed = float
Time = float

