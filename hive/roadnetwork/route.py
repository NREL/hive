from typing import NamedTuple, Tuple

from hive.roadnetwork.routestep import RouteStep


class Route(NamedTuple):
    """
    contains the route, distance, and time estimate
    """
    route: Tuple[RouteStep, ...]
    total_distance: float
    total_travel_time: float

    def is_empty(self):
        return len(self.route) == 0

    def has_route(self):
        return not self.is_empty()

    @classmethod
    def empty(cls):
        return cls((), 0.0, 0.0)
