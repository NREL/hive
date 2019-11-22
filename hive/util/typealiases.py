from typing import Tuple
# from hive.roadnetwork.link import Link

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
# Route = Tuple[Link, ...]

# NUMERICAL TYPES
# todo: Pints library!
KwH = float
Km = float
Percentage = float
Speed = float
Time = float

