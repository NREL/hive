from __future__ import annotations

from typing import NamedTuple, Tuple

from hive.roadnetwork.link import Link
from hive.util.helpers import TupleOps


class Route(NamedTuple):
    """
    contains the route, distance, and time estimate
    """
    route: Tuple[Link, ...]
    total_distance: float
    total_travel_time: float

    def is_empty(self):
        return len(self.route) == 0

    def has_route(self):
        return not self.is_empty()

    def step_route(self) -> Tuple[Link, Route]:
        route_step, remaining_route = TupleOps.head_tail(self.route)
        return route_step, self._replace(route=remaining_route)



    @classmethod
    def empty(cls):
        return cls((), 0.0, 0.0)
