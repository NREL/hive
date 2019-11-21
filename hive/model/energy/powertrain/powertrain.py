from __future__ import annotations

from abc import ABC, abstractmethod

from hive.model.energy.energytype import EnergyType
from hive.roadnetwork.route import Route
from hive.roadnetwork.routetraversal import RouteTraversal
from hive.util.typealiases import KwH, PowertrainId


class Powertrain(ABC):
    """
    a powertrain has a behavior where it calculate energy consumption in KwH
    """

    @abstractmethod
    def get_id(self) -> PowertrainId:
        pass

    @abstractmethod
    def get_energy_type(self) -> EnergyType:
        """
        gets the energy type of this Powertrain model
        :return: an energy type
        """
        pass

    @abstractmethod
    def energy_cost(self, route: Route, route_traversal: RouteTraversal) -> KwH:
        """
        (estimated) energy cost to traverse this route
        :param route: a route
        :param route_traversal: the experienced route traversal
        :return: energy cost
        """
        pass

