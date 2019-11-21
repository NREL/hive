from __future__ import annotations

from typing import NamedTuple, Optional

from hive.config.environment import ROUTESTEP_DIST_KM
from hive.util.typealiases import *


class Position(NamedTuple):
    """
    A specific location as defined by a link and a percentage from the origin.
    Includes optional routestep pointer.
    """
    link_id: LinkId
    percent_from_origin: Percentage


class RouteStep(NamedTuple):
    """
    A single discrete step of a route. The step distance is determined as a function of the h3 edge width.
    """
    link_id: LinkId
    geo_id: GeoId

    experienced_time_s: Optional[float]
    DISTANCE: Km = ROUTESTEP_DIST_KM

    def add_experienced_time(self, time: float):
        return self._replace(experienced_time_s=time)


class Route(NamedTuple):
    """
    contains the route, distance, and time estimate
    """
    route: Tuple[RouteStep, ...]
    total_travel_time: float
    total_travel_distance: float
    route_step_pointer: RouteStepPointer

    def step(self) -> Optional[Tuple[Route, RouteStep]]:
        if not self.at_end():
            route_step = self.current_route_step()
            return self._replace(route_step_pointer=self.route_step_pointer + 1), route_step
        else:
            return None

    def current_route_step(self) -> Optional[RouteStep]:
        if not self.at_end():
            return self.route[self.route_step_pointer]
        else:
            return None

    def at_end(self) -> bool:
        return self.route_step_pointer >= len(self.route)

    def is_empty(self) -> bool:
        return len(self.route) == 0

    @classmethod
    def empty(cls):
        return cls((), 0.0, 0.0)


class ExperiencedRouteSteps(NamedTuple):
    """
    Very similar to a route but used to describe links that have already been traversed by a vehicle.
    This is then fed into the vehicle PowerTrain to determine energy usage.
    """
    links: Tuple[RouteStep, ...]
    total_experienced_time: float
    total_experienced_distance: float
