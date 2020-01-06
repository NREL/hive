from __future__ import annotations

from typing import NamedTuple

from h3 import h3

from hive.util.helpers import H3Ops
from hive.util.typealiases import LinkId, GeoId
from hive.util.units import unit, km, Ratio


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


def link_distance(link: Link) -> km:
    """
    determines the distance of a link

    :param link: some road network link, possibly with a different start/end point from
    the matching link in the road network
    :rtype: :py:obj:`kilometers`
    :return: the distance of this link, in kilometers
    """
    return H3Ops.great_circle_distance(link.start, link.end)
