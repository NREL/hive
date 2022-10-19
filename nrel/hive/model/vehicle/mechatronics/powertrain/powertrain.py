from __future__ import annotations

from abc import abstractmethod, ABC

from nrel.hive.model.roadnetwork.route import Route


class Powertrain(ABC):
    """
    a powertrain has the behavior where it calculate energy consumption in KwH
    """
    @property
    @abstractmethod
    def speed_units(self) -> str:
        pass

    @property
    @abstractmethod
    def distance_units(self) -> str:
        pass

    @property
    @abstractmethod
    def energy_units(self) -> str:
        pass

    @abstractmethod
    def energy_cost(self, route: Route) -> float:
        """
        (estimated) energy cost to traverse this route


        :param route: a route, either experienced, or, estimated
        :return: energy cost of this route
        """
