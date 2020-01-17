from typing import Tuple

from hive.model.roadnetwork.property_link import PropertyLink
from hive.util.units import km

Route = Tuple[PropertyLink, ...]
"""
any route in the system is a tuple of PropertyLinks
"""


def route_distance_km(route: Route) -> km:
    """
    Return the distance of the route in kilometers

    :param route: route to calculate distance on
    :rtype: :py:obj:`kilometers`
    :return: the distance in kilometers
    """
    distance_km = 0
    for pl in route:
        distance_km += pl.distance_km

    return distance_km
