from typing import Tuple, Optional

import functools as ft

import h3

from hive.model.roadnetwork.link import Link
from hive.runner import Environment
from hive.util import TupleOps, wkt
from hive.util.typealiases import GeoId
from hive.util.units import Kilometers, Seconds

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


def route_travel_time_seconds(route: Route) -> Seconds:
    """
    returns the travel time, in seconds, for a route

    :param route: route to calculate time from
    :return: the travel time, in seconds
    """
    tt = ft.reduce(lambda acc, l: acc + l.travel_time_seconds, route, 0.0)
    return int(tt)


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


def to_linestring(route: Route, env: Environment) -> str:
    """
    converts the traversal to a WKT linestring or an empty polygon if the traversal was empty
    see https://en.wikipedia.org/wiki/Well-known_text_representation_of_geometry

    :param route: a route
    :return: a linestring or an empty WKT
    """
    if len(route) == 0:
        return wkt.polygon_empty()
    elif len(route) == 1:
        link = route[0]
        src = h3.h3_to_geo(link.start)
        dst = h3.h3_to_geo(link.end)
        linestring = wkt.linestring_2d((src, dst), env.config.global_config.wkt_x_y_ordering)
        return linestring
    else:
        points = ft.reduce(lambda acc, l: acc + (h3.h3_to_geo(l.start), h3.h3_to_geo(l.end)), route, ())
        linestring = wkt.linestring_2d(points, env.config.global_config.wkt_x_y_ordering)
        return linestring
