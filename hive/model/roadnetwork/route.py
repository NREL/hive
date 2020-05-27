from typing import Tuple, Optional

from hive.model.roadnetwork.link import Link
from hive.util import TupleOps
from hive.util.typealiases import GeoId
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


def valid_route(route: Route,
                src: GeoId,
                dst: Optional[GeoId] = None) -> bool:
    """
    checks if the route is valid

    todo: we should check that the route is valid from a graph perspective here as well.
      we could step through the route via the road network and test that each link is incident

    :param route: the provided route
    :param src: the GeoId of the vehicle starting this route
    :param dst: the GeoId of the entity which is the destination for this route
                if omitted, only source is checked
    :return: whether the route is valid
    """
    if TupleOps.is_empty(route):
        # an empty route is valid if no destination is being confirmed or if the src matches the dst
        return not dst or src == dst
    elif not dst:
        return src == TupleOps.head(route).start
    else:
        return src == TupleOps.head(route).start and dst == TupleOps.last(route).end
