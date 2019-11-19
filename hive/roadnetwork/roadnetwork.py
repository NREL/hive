from __future__ import annotations

from abc import ABC, abstractmethod

from hive.roadnetwork.route import Route, Position
from hive.roadnetwork.routetraversal import RouteTraversal
from hive.util.typealiases import GeoId, LinkId


class RoadNetwork(ABC):
    """
    a class that contains an updated model of the road network state and
    is used to compute routes for agents in the simulation
    """
    @abstractmethod
    def route_by_geoid(self, origin: GeoId, destination: GeoId) -> Route:
        pass

    @abstractmethod
    def route_by_position(self, origin: Position, destination: Position) -> Route:
        pass

    @abstractmethod
    def update(self, sim_time: int) -> RoadNetwork:
        """
        gives the RoadNetwork a chance to update it's flow network based on the current simulation time
        :param sim_time: the sim time to update the model to
        :return: does not return
        """
        pass

    @abstractmethod
    def get_link_speed(self, link_id: LinkId) -> float:
        """
        gets the current link speed for the provided Position
        :param link_id: the location on the road network
        :return: speed
        """
        pass

    @abstractmethod
    def compute_route_traversal(self, route: Route) -> RouteTraversal:
        """

        :param route:
        :return:
        """
        pass

    @abstractmethod
    def position_to_geoid(self, postition: Position, resolution: int) -> GeoId:
        """
        does the work to determine the coordinate of this position on the road network
        :param link_id: a position on the road network
        :param resolution: h3 resolution
        :return: an h3 geoid at this position
        """
        pass

    @abstractmethod
    def geoid_within_geofence(self, geoid: GeoId) -> bool:
        """
        confirms that the coordinate exists within the bounding polygon of this road network instance
        :param geoid: an h3 geoid
        :return: True/False
        """
        pass

    @abstractmethod
    def link_id_within_geofence(self, link_id: LinkId) -> bool:
        """
        confirms that the coordinate exists within the bounding polygon of this road network instance
        :param link_id: a position on the road network across the entire simulation
        :return: True/False
        """
        pass

    @abstractmethod
    def geoid_within_simulation(self, geoid: GeoId) -> bool:
        """
        confirms that the coordinate exists within the bounding polygon the entire simulation,
        which may include many (distributed) RoadNetwork instances
        :param geoid: an h3 geoid
        :return: True/False
        """
        pass

    @abstractmethod
    def link_id_within_simulation(self, link_id: LinkId) -> bool:
        """
        confirms that the coordinate exists within the bounding polygon the entire simulation,
        which may include many (distributed) RoadNetwork instances
        :param link_id: a position on the road network across the entire simulation
        :return: True/False
        """
        pass

