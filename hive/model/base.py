from typing import NamedTuple

from hive.model.coordinate import Coordinate
from hive.util.typealiases import BaseId, GeoId


class Base(NamedTuple):
    id: BaseId
    coordinate: Coordinate
    geoid: GeoId
