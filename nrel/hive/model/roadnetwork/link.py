from __future__ import annotations

from typing import NamedTuple, Optional

import h3

from nrel.hive.model.roadnetwork.linktraversal import LinkTraversal
from nrel.hive.util.h3_ops import H3Ops
from nrel.hive.util.typealiases import LinkId, GeoId
from nrel.hive.util.units import (
    Kilometers,
    Kmph,
    Seconds,
    Ratio,
    hours_to_seconds,
)


class Link(NamedTuple):
    """
    a directed edge on the road network from node a -> node b
    the LinkId is used for lookup of link attributes
    the o/d pair of GeoIds is the start and end locations along this
    link. in the case of the RoadNetwork, these are (strictly) members of
    the vertex set. an agent route may also use a Link to represent
    a partial link traversal, using an o/d pair which is within the link but
    not necessarily the end-points.


    :param link_id: The unique link id.
    :type link_id: :py:obj:`LinkId`

    :param start: The starting endpoint of the link
    :type start: :py:obj:`GeoId`

    :param end: The ending endpoint of the link
    :type end: :py:obj:`GeoId`
    """

    link_id: LinkId
    start: GeoId
    end: GeoId
    distance_km: Kilometers
    speed_kmph: Kmph

    @property
    def travel_time_seconds(self) -> Seconds:
        return hours_to_seconds(self.distance_km / self.speed_kmph)

    @classmethod
    def build(
        cls,
        link_id: LinkId,
        start: GeoId,
        end: GeoId,
        speed_kmph: Kmph,
        distance_km: Optional[Kilometers] = None,
    ) -> Link:
        if not distance_km:
            distance_km = H3Ops.great_circle_distance(start, end)
        return Link(
            link_id=link_id,
            start=start,
            end=end,
            distance_km=distance_km,
            speed_kmph=speed_kmph,
        )

    def update_speed(self, speed_kmph: Kmph) -> Link:
        """
        Update the speed of the property link


        :param speed_kmph: speed to update to
        :return: an updated PropertyLink
        """
        return self._replace(speed_kmph=speed_kmph)

    def to_link_traversal(self) -> LinkTraversal:
        """
        convert to a link traversal

        :return: the new link traversal
        """
        return LinkTraversal(
            self.link_id,
            self.start,
            self.end,
            self.distance_km,
            self.speed_kmph,
        )


def interpolate_between_geoids(a: GeoId, b: GeoId, ratio: Ratio) -> GeoId:
    """
    Interpolate between two geoids given a ratio from a->b


    :param a: The starting point

    :param b: The ending point

    :param ratio: The ratio from a->b
    :return: An interpolated GeoId
    """
    line = h3.h3_line(a, b)
    index = int(len(line) * ratio)

    return line[index]
