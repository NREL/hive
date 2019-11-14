from __future__ import annotations

from abc import ABC, abstractmethod

from hive.roadnetwork.route import Route
from hive.roadnetwork.position import Position
from hive.util.typealiases import GeoId


class RoadNetwork(ABC):
    """
    a class that contains an updated model of the road network state and
    is used to compute routes for agents in the simulation
    """
    @abstractmethod
    def route(self, origin: Position, destination: Position) -> Route:
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
    def geoid_to_position(self, geoid: GeoId) -> Position:
        """
        finds the closest RoadNetwork Position to the provided coordinate
        :param geoid: an h3 geoid
        :return: a Position, which may be RoadNetwork-dependent
        """

    @abstractmethod
    def position_to_geoid(self, position: Position) -> GeoId:
        """
        does the work to determine the coordinate of this position on the road network
        :param position: a position on the road network
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

    @abstractmethod
    def position_within_geofence(self, position: Position) -> bool:
        """
        confirms that the coordinate exists within the bounding polygon of this road network instance
        :param position: a position on the road network across the entire simulation
        :return: True/False
        """

    @abstractmethod
    def geoid_within_simulation(self, geoid: GeoId) -> bool:
        """
        confirms that the coordinate exists within the bounding polygon the entire simulation,
        which may include many (distributed) RoadNetwork instances
        :param geoid: an h3 geoid
        :return: True/False
        """

    @abstractmethod
    def position_within_simulation(self, position: Position) -> bool:
        """
        confirms that the coordinate exists within the bounding polygon the entire simulation,
        which may include many (distributed) RoadNetwork instances
        :param position: a position on the road network across the entire simulation
        :return: True/False
        """

