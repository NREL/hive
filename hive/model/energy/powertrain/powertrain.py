from __future__ import annotations

from abc import ABC, abstractmethod

from hive.model.energy.energytype import EnergyType
from hive.model.roadnetwork.route import Route
from hive.util.typealiases import PowertrainId
from hive.util.units import kwh


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
        pass

    @abstractmethod
    def get_energy_type(self) -> EnergyType:
        """
        gets the energy type of this Powertrain model

        :return: an energy type
        """
        pass

    @abstractmethod
    def energy_cost(self, route: Route) -> kwh:
        """
        (estimated) energy cost to traverse this route

        :param route: a route, either experienced, or, estimated
        :return: energy cost of this route
        """
        pass

