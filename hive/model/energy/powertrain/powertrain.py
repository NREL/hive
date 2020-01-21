from __future__ import annotations

from abc import ABC, abstractmethod

from hive.model.energy.energytype import EnergyType
from hive.model.roadnetwork.route import Route
from hive.util.typealiases import PowertrainId
from hive.util.units import KwH


class Powertrain(ABC):
    """
    a powertrain has the behavior where it calculate energy consumption in KwH
    """

    @abstractmethod
    def get_id(self) -> PowertrainId:
        """
        Gets the id of the Powertrain

        :return: the powertrain id
        """

    @abstractmethod
    def get_energy_type(self) -> EnergyType:
        """
        gets the energy type of this Powertrain model

        :return: an energy type
        """

    @abstractmethod
    def energy_cost(self, route: Route) -> KwH:
        """
        (estimated) energy cost to traverse this route

        :param route: a route, either experienced, or, estimated
        :return: energy cost of this route
        """

