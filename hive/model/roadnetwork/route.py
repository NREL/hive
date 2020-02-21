from typing import Tuple

from hive.model.roadnetwork.link import Link
from hive.util.units import Kilometers

Route = Tuple[Link, ...]
"""
any route in the system is a tuple of PropertyLinks
"""


def route_distance_km(route: Route) -> Kilometers:
    """
    Return the distance of the route in kilometers

    :param route: route to calculate distance on
    :rtype: :py:obj:`kilometers`
    :return: the distance in kilometers
    """
    distance_km = 0
    for l in route:
        distance_km += l.distance_km

    return distance_km
