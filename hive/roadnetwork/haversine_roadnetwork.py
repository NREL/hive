from __future__ import annotations

from typing import Tuple

from hive.roadnetwork.roadnetwork import RoadNetwork
from hive.roadnetwork.route import Route, Position
from hive.roadnetwork.routetraversal import RouteTraversal
from hive.util.typealiases import GeoId, LinkId
from hive.model.coordinate import (
    dist_geoid_haversine,
    geoid_to_coordinate,
    coordinate_to_geoid,
    interpolate_between_coordinates,
)


class HaversineRoadNetwork(RoadNetwork):
    """
    Implements a simple haversine road network where a unique node exists for each unique GeoId in the simulation.
    This assumes a fully connected graph between each node in which the shortest path is the link that connects any
    two nodes. LinkId is specified as a concatenation of the GeoId of its endpoints in which the order is given by
    origin and destination respectively.
    """

    # TODO: Replace speed with more accurate/dynamic estimate.
    _AVG_SPEED = 40  # km/hour

    def _node_ids_from_link_id(self, link_id: LinkId) -> Tuple[GeoId, GeoId]:
        nodes = link_id.split("-")
        a = nodes[0]
        b = nodes[1]
        return a, b

    def route_by_geoid(self, origin: GeoId, destination: GeoId) -> Route:
        link_id = origin + "-" + destination
        link_distance = dist_geoid_haversine(origin, destination)

        route_time_estimate = link_distance / self._AVG_SPEED  # hr

        return Route((Position(link_id, 0), Position(link_id, 1)), link_distance, route_time_estimate)

    def route_by_position(self, origin: Position, destination: Position) -> Route:
        origin_geoid = self.position_to_geoid(origin)
        destination_geoid = self.position_to_geoid(destination)
        return self.route_by_geoid(origin_geoid, destination_geoid)

    def compute_route_traversal(self, route: Route) -> RouteTraversal:
        raise NotImplementedError("This method has not yet been implemented")

    def update(self, sim_time: int) -> RoadNetwork:
        """
        gives the RoadNetwork a chance to update it's flow network based on the current simulation time
        :param sim_time: the sim time to update the model to
        :return: does not return
        """

        # This particular road network doesn't keep track of network flow so this method does nothing.
        pass

    def get_link_speed(self, link_id: LinkId) -> float:
        """
        gets the current link speed for the provided Position
        :param link_id: the location on the road network
        :return: speed
        """
        return self._AVG_SPEED

    def postition_to_geoid(self, position: Position, resolution: int) -> GeoId:
        """
        does the work to determine the coordinate of this position on the road network
        :param link_id: a position on the road network
        :param resolution: h3 resolution
        :return: an h3 geoid at this position
        """
        node_a_geoid, node_b_geoid = self._node_ids_from_link_id(position.link_id)
        node_a_coord = geoid_to_coordinate(node_a_geoid)
        node_b_coord = geoid_to_coordinate(node_b_geoid)

        node_c_coord = interpolate_between_coordinates(node_a_coord, node_b_coord)

        # TODO: Consolidate all references to h3 resolution.
        return coordinate_to_geoid(node_c_coord, 11)

    def geoid_within_geofence(self, geoid: GeoId) -> bool:
        """
        confirms that the coordinate exists within the bounding polygon of this road network instance
        :param geoid: an h3 geoid
        :return: True/False
        """
        raise NotImplementedError("This method has not yet been implemented.")

    def link_id_within_geofence(self, link_id: LinkId) -> bool:
        """
        confirms that the coordinate exists within the bounding polygon of this road network instance
        :param link_id: a position on the road network across the entire simulation
        :return: True/False
        """
        raise NotImplementedError("This method has not yet been implemented.")

    def geoid_within_simulation(self, geoid: GeoId) -> bool:
        """
        confirms that the coordinate exists within the bounding polygon the entire simulation,
        which may include many (distributed) RoadNetwork instances
        :param geoid: an h3 geoid
        :return: True/False
        """
        raise NotImplementedError("This method has not yet been implemented.")

    def link_id_within_simulation(self, link_id: LinkId) -> bool:
        """
        confirms that the coordinate exists within the bounding polygon the entire simulation,
        which may include many (distributed) RoadNetwork instances
        :param link_id: a position on the road network across the entire simulation
        :return: True/False
        """
        raise NotImplementedError("This method has not yet been implemented.")
