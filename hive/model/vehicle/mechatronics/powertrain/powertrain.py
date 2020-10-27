from __future__ import annotations

from abc import abstractmethod

from hive.model.roadnetwork.route import Route
from hive.util.abc_utils import abstract_attribute, ABCMeta


class Powertrain(metaclass=ABCMeta):
    """
    a powertrain has the behavior where it calculate energy consumption in KwH
    """
    @abstract_attribute
    def speed_units(self) -> str:
        pass

    @abstract_attribute
    def distance_units(self) -> str:
        pass

    @abstract_attribute
    def energy_units(self) -> str:
        pass

    @abstractmethod
    def energy_cost(self, route: Route) -> float:
        """
        (estimated) energy cost to traverse this route


        :param route: a route, either experienced, or, estimated
        :return: energy cost of this route
        """
