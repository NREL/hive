from typing import NamedTuple, Tuple

from hive.util.typealiases import *
from hive.roadnetwork.route import Position


class LinkTraversal(NamedTuple):
    """
    represents experienced travel over a link
    """
    link_id: LinkId
    travel_time: float
    travel_distance: float
    # grade: float <- later, and, room for adding other attributes as necessary


class RouteTraversal(NamedTuple):
    """
    represents experienced travel over several links
    """
    route: Tuple[LinkTraversal, ...]
    start_pos: Position
    end_pos: Position
    start_geoid: GeoId
    end_geoid: GeoId
