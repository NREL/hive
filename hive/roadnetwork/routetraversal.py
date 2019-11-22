from __future__ import annotations

import functools as ft
from typing import NamedTuple
from typing import Optional, Union

from hive.roadnetwork.linktraversal import LinkTraversal
from hive.roadnetwork.linktraversal import traverse_up_to
from hive.roadnetwork.link import Link
from hive.roadnetwork.roadnetwork import RoadNetwork
from hive.util.helpers import TupleOps
from hive.util.typealiases import *


class RouteTraversal(NamedTuple):
    remaining_time: Time = 0
    experienced_route: Tuple[Link, ...] = ()
    remaining_route: Tuple[Link, ...] = ()

    def no_time_left(self):
        """
        if we have no more time, then end the traversal
        :return: True if the agent is out of time
        """
        return self.remaining_time == 0

    def add_traversal(self, t: LinkTraversal) -> RouteTraversal:
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
        return self._replace(
            remaining_time=t.remaining_time,
            experienced_route=updated_experienced_route,
            remaining_route=updated_remaining_route,
        )

    def add_link_not_traversed(self, link: Link) -> RouteTraversal:
        """
        if a link wasn't traversed, be sure to add it to the remaining route
        :param link: a link for the remaining route
        :return: the updated RouteTraversal
        """
        return self._replace(
            remaining_route=self.remaining_route + (link,)
        )


def traverse(route_estimate: Tuple[Link, ...],
             road_network: RoadNetwork,
             time_step: Time) -> Optional[Union[Exception, RouteTraversal]]:
    """
    step through the route from the current agent position (assumed to be start.link_id) toward the destination
    :param route_estimate: the current route estimate
    :param road_network: the current road network state
    :param time_step: size of the time step for this traversal
    :return: a route experience and updated route estimate;
             or, nothing if the route is consumed.
             an exception is possible if the current step is not found on the link or
             the route is malformed.
    """
    if len(route_estimate) == 0:
        return None
    elif TupleOps.head(route_estimate).o == TupleOps.last(route_estimate).d:
        return None
    else:

        # function that steps through the route
        def _traverse(acc: Tuple[RouteTraversal, Optional[Exception]],
                      x: Link) -> Tuple[RouteTraversal, Optional[Exception]]:
            acc_traversal, acc_failures = acc
            if acc_traversal.no_time_left():
                return acc_traversal.add_link_not_traversed(x), acc_failures
            else:
                # traverse this link as far as we can go
                traverse_result = traverse_up_to(road_network, x, acc_traversal.remaining_time)
                if isinstance(traverse_result, Exception):
                    return acc_traversal, traverse_result
                else:
                    updated_experienced_route = acc_traversal.add_traversal(traverse_result)
                    return updated_experienced_route, acc_failures

        # initial search state has a route traversal and an Optional[Exception]
        initial = (RouteTraversal(remaining_time=time_step), None)

        traversal_result, error = ft.reduce(
            _traverse,
            route_estimate,
            initial
        )

        if error is not None:
            return error
        else:
            return traversal_result
