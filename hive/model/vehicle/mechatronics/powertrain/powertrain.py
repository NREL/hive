from __future__ import annotations

from abc import ABC, abstractmethod

from hive.model.roadnetwork.route import Route
from hive.util.units import KwH


class Powertrain(ABC):
    """
    a powertrain has the behavior where it calculate energy consumption in KwH
    """

    @abstractmethod
    def energy_cost(self, route: Route) -> KwH:
        """
        (estimated) energy cost to traverse this route

        :param route: a route, either experienced, or, estimated
        :return: energy cost of this route
        """
