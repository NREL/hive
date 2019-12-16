from typing import Tuple

from hive.model.roadnetwork.property_link import PropertyLink
from hive.util.units import unit, km

Route = Tuple[PropertyLink, ...]
"""
any route in the system is a tuple of PropertyLinks
"""


def route_distance(route: Route) -> km:
    distance = 0 * unit.kilometers
    for pl in route:
        distance += pl.distance

    return distance
