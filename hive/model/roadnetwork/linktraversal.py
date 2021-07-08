from __future__ import annotations

from typing import Optional, NamedTuple, Tuple

from hive.util.h3_ops import H3Ops, LinkId, GeoId
from hive.util.units import Seconds, Kilometers, Kmph, hours_to_seconds


class LinkTraversal(NamedTuple):
    """
    represents either an intention to traverse some or all of a link
    or, an experience over some or all of a link
    """
    link_id: LinkId
    start: GeoId
    end: GeoId

    distance_km: Kilometers

    # TODO: this should come from the road network in real time to support variable link speeds
    speed_kmph: Kmph

    @classmethod
    def build(
            cls,
            link_id: LinkId,
            start: GeoId,
            end: GeoId,
            speed_kmph: Kmph,
            distance_km: Optional[Kilometers] = None,
    ) -> LinkTraversal:
        if not distance_km:
            distance_km = H3Ops.great_circle_distance(start, end)
        return LinkTraversal(
            link_id=link_id,
            start=start,
            end=end,
            distance_km=distance_km,
            speed_kmph=speed_kmph,
        )

    @property
    def travel_time_seconds(self) -> Seconds:
        return hours_to_seconds(self.distance_km / self.speed_kmph)

    def update_start(self, new_start: GeoId) -> LinkTraversal:
        """
        changes the start GeoId of the (experienced) LinkTraversal. used to set trip positions on
        partially-traversed Links or to set a location of a stationary entity.

        :param new_start: the new start GeoId (should be a position along the h3_line between
                          Link.start and Link.end)

        :return: the link with an updated start GeoId
        """
        if new_start == self.start:
            return self
        else:
            return self._replace(start=new_start)

    def update_end(self, new_end: GeoId) -> LinkTraversal:
        """
        changes the end GeoId of the (experienced) LinkTraversal. used to set trip positions on
        partially-traversed Links or to set a location of a stationary entity.

        :param new_end: the new end GeoId (should be a position along the h3_line between
                          Link.start and Link.end)

        :return: the link with an updated end GeoId
        """
        if new_end == self.end:
            return self
        else:
            return self._replace(end=new_end)


class LinkTraversalResult(NamedTuple):
    """
    the result from a vehicle moving over a link traversal.

    :param traversed: represents any part of the link that was traversed.
    :param remaining: represents any part of the link that remains to be traversed
    :param remaining_time_seconds: represents any time the agent has left to traverse additional links

    """
    traversed: Optional[LinkTraversal]
    remaining: Optional[LinkTraversal]
    remaining_time_seconds: Seconds


def traverse_up_to(link: LinkTraversal,
                   available_time_seconds: Seconds) -> Tuple[Optional[Exception], Optional[LinkTraversalResult]]:
    """
    using the ground truth road network, and some agent Link traversal, attempt to traverse
    the link, based on travel time calculations from the Link's PropertyLink attributes.


    :param link: the plan the agent has to traverse a subset of a road network link

    :param available_time_seconds: the remaining time the agent has in this time step
    :return: the updated traversal, or, an exception.
             on update, if there is any remaining traversal, return an updated Link.
             if no traversal remains, return None.
             regardless, return the agent's remaining time after traversing
             if there was any error, return the exception instead.
    """
    if link is None:
        return AttributeError(f"attempting to traverse link which does not exist"), None
    elif link.start == link.end:
        # already done!
        result = LinkTraversalResult(
            traversed=None,
            remaining=None,
            remaining_time_seconds=available_time_seconds
        )
        return None, result
    else:
        # traverse up to available_time_hours across this link
        if link.travel_time_seconds <= available_time_seconds:
            # we can complete this link, so we return (remaining) Link = None
            result = LinkTraversalResult(
                traversed=link,
                remaining=None,
                remaining_time_seconds=(available_time_seconds - link.travel_time_seconds)
            )
            return None, result
        else:
            # we do not have enough time to finish traversing this link, so, just traverse part of it,
            # leaving no remaining time.

            # find the point in this link to split into two sub-links
            mid_geoid = H3Ops.point_along_link(link, available_time_seconds)

            # create two sub-links, one for the part that was traversed, and one for the remaining part
            traversed = LinkTraversal.build(link.link_id, link.start, mid_geoid, speed_kmph=link.speed_kmph)
            remaining = LinkTraversal.build(link.link_id, mid_geoid, link.end, speed_kmph=link.speed_kmph)

            result = LinkTraversalResult(
                traversed=traversed,
                remaining=remaining,
                remaining_time_seconds=0,
            )
            return None, result
