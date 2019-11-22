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
    id: LinkId
    o: GeoId
    d: GeoId


class PropertyLink(NamedTuple):
    """
    a link on the road network which also has road network attributes
    """
    link_id: LinkId
    link: Link
    # todo: units here? python Pints library?
    distance: float
    speed: float
    travel_time: float
    # grade: float # nice in the future?'


def interpolate_between_geoids(a: GeoId, b: GeoId, percent: Percentage) -> GeoId:
    line = h3.h3_line(a, b)
    index = int(len(line) * percent)

    return line[index]
