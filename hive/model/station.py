from typing import NamedTuple

from hive.model.coordinate import Coordinate
from hive.util.typealiases import *


class Station(NamedTuple):
    id: StationId
    coordinate: Coordinate
    geoid: GeoId
