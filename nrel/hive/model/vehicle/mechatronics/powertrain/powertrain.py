from __future__ import annotations

from abc import abstractmethod, ABC
from dataclasses import dataclass

from nrel.hive.model.roadnetwork.route import Route


@dataclass(frozen=True)
class PowertrainMixin:
    speed_units: str
    distance_units: str
    energy_units: str


class PowertrainABC(ABC):
    """
    a powertrain has the behavior where it calculate energy consumption in KwH
    """

    @abstractmethod
    def energy_cost(self, route: Route) -> float:
        """
        (estimated) energy cost to traverse this route


        :param route: a route, either experienced, or, estimated
        :return: energy cost of this route
        """


class Powertrain(PowertrainMixin, PowertrainABC):
    """"""
