from __future__ import annotations

from abc import ABC, abstractmethod

from hive.model.energy.energytype import EnergyType
from hive.model.energy.energysource import EnergySource
from hive.util.typealiases import Kw, EnergyCurveId


class EnergyCurve(ABC):
    """
    a powertrain has a behavior where it calculate energy consumption in KwH
    """

    @abstractmethod
    def get_id(self) -> EnergyCurveId:
        pass

    @abstractmethod
    def get_energy_type(self) -> EnergyType:
        """
        gets the energy type of this Powertrain model
        :return: an energy type
        """
        pass

    @abstractmethod
    def energy_gain(self, energy_source: EnergySource) -> Kw:
        """
        (estimated) energy gain due to fueling, based on EnergySource
        :param energy_source: a vehicle's source of energy
        :return: energy that can be gained over this time
        """
        pass

