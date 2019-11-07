from abc import ABC, abstractmethod
from hive.roadnetwork.route import Route
from hive.model.position import Position


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
