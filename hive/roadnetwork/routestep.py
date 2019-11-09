from typing import NamedTuple

from hive.roadnetwork.position import Position
from hive.model.coordinate import Coordinate
from hive.roadnetwork.roadnetwork import RoadNetwork


class RouteStep(NamedTuple):
    """
    a single step of a route
    """
    position: Position
    distance: float
    # percent_complete: float
    # grade: float # nice in the future?'

    def to_coordinate(self, road_network: RoadNetwork) -> Coordinate:
        """
        this function is straight-forward for our current implementation using a
        euclidian space for routing. but, moving to a graph-based representation,
        we would need to identify the agent's current position along an edge to
        translate this to a coordinate.

        that would suggest that a Position, in the future, would have an edge id,
        and enough positional data (link_origin_coord, link_destination_coord) from
        which we could calculate current agent location.
        :return: a Coordinate for the agent
        """
        return self.position
