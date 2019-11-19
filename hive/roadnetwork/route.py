from __future__ import annotations

from typing import NamedTuple, Tuple

from hive.util.helpers import TupleOps
from hive.util.typealiases import *
from hive.roadnetwork.link import Link


class Position(NamedTuple):
    """
    A specific location as defined by a link and a percentage.
    """
    link_id: LinkId
    percent_from_origin: Percentage


class Route(NamedTuple):
    """
    contains the route, distance, and time estimate
    """
    route: Tuple[Position, ...]
    total_distance: float
    total_travel_time: float

    def is_empty(self):
        return len(self.route) == 0

    def step_route(self) -> Tuple[Link, Route]:
        route_step, remaining_route = TupleOps.head_tail(self.route)
        return route_step, self._replace(route=remaining_route)

    @classmethod
    def empty(cls):
        return cls((), 0.0, 0.0)


