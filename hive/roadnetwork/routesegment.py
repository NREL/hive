from typing import NamedTuple, Tuple

from hive.roadnetwork.link import Link


class RouteSegment(NamedTuple):
    """
    represents a segment traversed in a time step
    """
    start_link: Link
    connecting_links: Tuple[Link, ...]
    end_link: Link

