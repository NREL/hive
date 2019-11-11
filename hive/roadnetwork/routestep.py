from typing import NamedTuple

from hive.roadnetwork.position import Position


class RouteStep(NamedTuple):
    """
    a single step of a route
    """
    position: Position
    distance: float
    # percent_complete: float
    # grade: float # nice in the future?'
