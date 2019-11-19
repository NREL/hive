from typing import NamedTuple

from hive.util.typealiases import LinkId, Percentage
from hive.model.coordinate import Coordinate


class Link(NamedTuple):
    """
    a directed edge on the road network from node a -> node b
    """
    id: LinkId
    distance: float

    # TODO: Should these be coordinates or geoids?
    # a: Coordinate
    # b: Coordinate

    # grade: float # nice in the future?'
