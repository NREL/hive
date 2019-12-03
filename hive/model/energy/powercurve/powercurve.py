from __future__ import annotations

from abc import ABC, abstractmethod

from hive.model.energy.energytype import EnergyType
from hive.util.typealiases import PowercurveId, Time


class Powercurve(ABC):
    """
    a powertrain has a behavior where it calculate energy consumption in KwH
    """

    @abstractmethod
    def get_id(self) -> PowercurveId:
        pass

    @abstractmethod
    def get_energy_type(self) -> EnergyType:
        """
        gets the energy type of this Powertrain model
        :return: an energy type
        """
        pass

    @abstractmethod
    def refuel(self,
               energy_source: 'EnergySource',
               charger: 'Charger',
               duration_seconds: Time = 1) -> 'EnergySource':
        """
        (estimated) energy rate due to fueling, based on EnergySource
        :param energy_source: a vehicle's source of energy
        :param charger: has a capacity scaling effect on the energy_rate
        :param duration_seconds: the amount of time to charge for
        :return: energy rate in KwH for charging with the current state of the EnergySource
        """
        pass

