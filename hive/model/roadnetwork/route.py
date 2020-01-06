from typing import Tuple

from hive.model.roadnetwork.property_link import PropertyLink
from hive.util.units import unit, km

Route = Tuple[PropertyLink, ...]
"""
any route in the system is a tuple of PropertyLinks
"""


def route_distance(route: Route) -> km:
    """
    Return the distance of the route in kilometers

    :param route: route to calculate distance on
    :rtype: :py:obj:`kilometers`
    :return: the distance in kilometers
    """
    distance = 0 * unit.kilometers
    for pl in route:
        distance += pl.distance

    return distance
