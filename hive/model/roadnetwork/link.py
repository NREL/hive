from __future__ import annotations

from typing import NamedTuple

from h3 import h3

from hive.util.typealiases import LinkId, GeoId, Percentage


class Link(NamedTuple):
    """
    a directed edge on the road network from node a -> node b
    the LinkId is used for lookup of link attributes
    the o/d pair of GeoIds is the start and end locations along this
    link. in the case of the RoadNetwork, these are (strictly) members of
    the vertex set. an agent route may also use a Link to represent
    a partial link traversal, using an o/d pair which is within the link but
    not necessarily the end-points.
    """
    link_id: LinkId
    start: GeoId
    end: GeoId


def interpolate_between_geoids(a: GeoId, b: GeoId, percent: Percentage) -> GeoId:
    line = h3.h3_line(a, b)
    index = int(len(line) * percent)

    return line[index]


def link_distance(link: Link, avg_hex_dist: float) -> float:
    """
    determines the distance of a link
    :param link: some road network link, possibly with a different start/end point from
    the matching link in the road network
    :param avg_hex_dist: the average distance between hexes at the sim_h3_resolution
    :return: the distance of this link
    """
    return h3.h3_distance(link.start, link.end) * avg_hex_dist
