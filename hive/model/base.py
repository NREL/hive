from typing import NamedTuple

from hive.model.coordinate import Coordinate
from hive.util.typealiases import BaseId


class Base(NamedTuple):
    id: BaseId
    coordinate: Coordinate
