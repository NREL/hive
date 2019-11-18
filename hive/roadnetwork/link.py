from typing import NamedTuple

from hive.roadnetwork.position import Position
from hive.util.typealiases import Percentage


class Link(NamedTuple):
    """
    a single step of a route
    """
    position: Position
    distance: float
    percent_complete: Percentage = 0.0
    # grade: float # nice in the future?'
