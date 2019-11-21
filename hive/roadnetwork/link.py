from typing import NamedTuple

from hive.util.typealiases import LinkId, GeoId, Km, Percentage
from hive.config.environment import H3_RESOLUTION

from h3 import h3


class Link(NamedTuple):
    """
    a directed edge on the road network from node a -> node b
    """
    id: LinkId
    distance: float

    a: GeoId
    b: GeoId

    # grade: float # nice in the future?'


def dist_h3(a: GeoId, b: GeoId) -> Km:
    h3_dist = h3.h3_distance(a, b)
    cell_diameter_km = h3.edge_length(H3_RESOLUTION) * 2

    return h3_dist * cell_diameter_km


def interpolate_between_geoids(a: GeoId, b: GeoId, percent: Percentage) -> GeoId:
    line = h3.h3_line(a, b)
    index = int(len(line) * percent)

    return line[index]
