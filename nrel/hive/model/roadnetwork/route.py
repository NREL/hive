import functools as ft
from typing import Any, Tuple, Optional

import h3

from nrel.hive.model.entity_position import EntityPosition
from nrel.hive.model.roadnetwork.linktraversal import LinkTraversal
from nrel.hive.runner import Environment
from nrel.hive.util import TupleOps, wkt
from nrel.hive.util.units import Kilometers, Seconds

Route = Tuple[LinkTraversal, ...]


def empty_route() -> Route:
    return ()


def route_distance_km(route: Route) -> Kilometers:
    """
    Return the distance of the route in kilometers


    :param route: route to calculate distance on
    :rtype: :py:obj:`kilometers`
    :return: the distance in kilometers
    """
    distance_km = 0.0
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


def route_cooresponds_with_entities(
    route: Route, src: EntityPosition, dst: Optional[EntityPosition] = None
) -> bool:
    """
    validates that the route correctly corresponds with any related entities

    :param route: the route
    :param src: a source position
    :param dst: an optional destination position
    :return: if the route is valid for this src(/dst)
    """
    if TupleOps.is_empty(route):
        # an empty route is valid if no destination is being confirmed or if the src matches the dst
        is_valid = not dst or src == dst
        return is_valid
    else:
        start_link = route[0]
        if not dst:
            # just confirm the start link is correct
            is_valid = start_link.start == src.geoid
            return is_valid
        else:
            # confirm both src and dst
            end_link = route[-1]
            is_valid = start_link.start == src.geoid and end_link.end == dst.geoid
            return is_valid


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
        inital: Tuple[Any, ...] = ()
        points = ft.reduce(
            lambda acc, l: acc + (h3.h3_to_geo(l.start), h3.h3_to_geo(l.end)),
            route,
            inital,
        )
        linestring = wkt.linestring_2d(points, env.config.global_config.wkt_x_y_ordering)
        return linestring


def routes_are_connected(prev_route: Route, next_route: Route) -> bool:
    """
    tests the connectivity between two successive routes. if either route is
    empty, the test is trivially true, since any empty route joined with another
    route is not disconnected - allowing for edge cases in re-routing, such as
    calling a re-routings where two trips have the same destination.

    :param prev_route: the previous route
    :param next_route: the next route
    :return: true if the routes are connected, or if at least one route is empty
    """

    prev_link = TupleOps.head_optional(prev_route)
    next_link = TupleOps.last(next_route)
    connected = prev_link.end == next_link.start if prev_link and next_link else True
    return connected
