from abc import ABC, abstractmethod

from hive.model.coordinate import Coordinate
from hive.roadnetwork.route import Route
from hive.roadnetwork.position import Position


class RoadNetwork(ABC):
    """
    a class that contains an updated model of the road network state and
    is used to compute routes for agents in the simulation
    """
    @abstractmethod
    def route(self, origin: Position, destination: Position) -> Route:
        pass

    @abstractmethod
    def update(self, sim_time: int):
        """
        gives the RoadNetwork a chance to update it's flow network based on the current simulation time
        :param sim_time: the sim time to update the model to
        :return: does not return
        """
        pass

    @abstractmethod
    def coordinate_to_position(self, coordinate: Coordinate) -> Position:
        """
        finds the closest RoadNetwork Position to the provided coordinate
        :param coordinate: a lat/lon pair
        :return: a Position, which may be RoadNetwork-dependent
        """

    @abstractmethod
    def position_to_coordinate(self, position: Position) -> Coordinate:
        """
        does the work to determine the coordinate of this position on the road network
        :param position: a position on the road network
        :return: the coordinate at this position
        """
        pass

    @abstractmethod
    def coordinate_within_geofence(self, coordinate: Coordinate) -> bool:
        """
        confirms that the coordinate exists within the bounding polygon of this road network instance
        :param coordinate: a lat/lon pair
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
    def coordinate_within_simulation(self, coordinate: Coordinate) -> bool:
        """
        confirms that the coordinate exists within the bounding polygon the entire simulation,
        which may include many (distributed) RoadNetwork instances
        :param coordinate: a lat/lon pair
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

