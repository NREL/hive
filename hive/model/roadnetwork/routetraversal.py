from __future__ import annotations

import functools as ft
from typing import Optional, NamedTuple

from hive.model.roadnetwork.linktraversal import LinkTraversalResult, LinkTraversal
from hive.model.roadnetwork.linktraversal import traverse_up_to
from hive.model.roadnetwork.route import Route
from hive.util import TupleOps
from hive.util.typealiases import *
from hive.util.units import Kilometers, Seconds


class RouteTraversal(NamedTuple):
    """
    A tuple that represents the result of traversing a route.


    :param remaining_time: The (estimated) time remaining in the route.
    :type remaining_time_seconds: :py:obj:`hours`

    :param travel_distance: The distance of the experienced route.
    :type travel_distance: :py:obj:`kilometers`

    :param experienced_route: The route that was traversed during a traversal.
    :type experienced_route: :py:obj:`Route`

    :param remaining_route: The route that remains after a traversal.
    :type remaining_route: :py:obj:`Route`
    """
    remaining_time_seconds: Seconds = 0
    traversal_distance_km: Kilometers = 0
    experienced_route: Route = ()
    remaining_route: Route = ()

    def no_time_left(self):
        """
        if we have no more time, then end the traversal

        :return: True if the agent is out of time
        """
        return self.remaining_time_seconds == 0.0

    def add_traversal(self, t: LinkTraversalResult) -> RouteTraversal:
        """
        take the result of a link traversal and update the route traversal


        :param t: a link traversal
        :return: the updated route traversal
        """
        updated_experienced_route = self.experienced_route \
            if t.traversed is None \
            else self.experienced_route + (t.traversed,)
        updated_remaining_route = self.remaining_route \
            if t.remaining is None \
            else self.remaining_route + (t.remaining,)
        if t.traversed:
            traversal_distance = self.traversal_distance_km + t.traversed.distance_km
        else:
            traversal_distance = self.traversal_distance_km
        return self._replace(
            remaining_time_seconds=t.remaining_time_seconds,
            traversal_distance_km=traversal_distance,
            experienced_route=updated_experienced_route,
            remaining_route=updated_remaining_route,
        )

    def add_link_not_traversed(self, link: LinkTraversal) -> RouteTraversal:
        """
        if a link wasn't traversed, be sure to add it to the remaining route


        :param link: a link traversal for the remaining route
        :return: the updated RouteTraversal
        """
        return self._replace(
            remaining_route=self.remaining_route + (link,)
        )


def traverse(route_estimate: Route,
             duration_seconds: Seconds) -> Tuple[Optional[Exception], RouteTraversal]:
    """
    step through the route from the current agent position (assumed to be start.link_id) toward the destination


    :param route_estimate: the current route estimate

    :param duration_seconds: size of the time step for this traversal, in seconds
    :return: a route experience and updated route estimate;
             or, nothing (None, Empty RouteTraversal) if the route is consumed.
             an exception is possible if the current step is not found on the link or
             the route is malformed.
    """
    if len(route_estimate) == 0:
        return None, RouteTraversal() 
    elif TupleOps.head(route_estimate).start == TupleOps.last(route_estimate).end:
        return None, RouteTraversal() 
    else:

        # function that steps through the route
        def _traverse(acc: Tuple[Optional[Exception], Optional[RouteTraversal]],
                      link: LinkTraversal) -> Tuple[Optional[Exception], Optional[RouteTraversal]]:
            acc_failures, acc_traversal = acc
            if acc_traversal.no_time_left():
                return acc_failures, acc_traversal.add_link_not_traversed(link)
            # traverse this link as far as we can go
            error, traverse_result = traverse_up_to(link, acc_traversal.remaining_time_seconds)
            if error:
                response = Exception(f"failure during traverse")
                response.__cause__ = error
                return response, None
            else:
                updated_experienced_route = acc_traversal.add_traversal(traverse_result)
                return acc_failures, updated_experienced_route

        # initial search state has a route traversal and an Optional[Exception]
        initial = (None, RouteTraversal(remaining_time_seconds=duration_seconds))

        result = ft.reduce(_traverse, route_estimate, initial)

        return result
