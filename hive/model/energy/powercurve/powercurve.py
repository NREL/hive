from __future__ import annotations

from typing import TYPE_CHECKING

from abc import ABC, abstractmethod

from hive.model.energy.energytype import EnergyType
from hive.util.typealiases import PowercurveId, SimTime

if TYPE_CHECKING:
    from hive.model.energy.charger import Charger
    from hive.model.energy.energysource import EnergySource


class Powercurve(ABC):
    """
    a powertrain has a behavior where it calculates energy consumption in KwH
    """

    @abstractmethod
    def get_id(self) -> PowercurveId:
        """
        Gets the id of the power curve

        :return: PowercurveId
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
    def refuel(self,
               energy_source: EnergySource,
               charger: Charger,
               duration_seconds: SimTime = 1) -> EnergySource:
        """
        (estimated) energy rate due to fueling, based on EnergySource

        :param energy_source: a vehicle's source of energy
        :param charger: has a capacity scaling effect on the energy_rate
        :param duration_seconds: the amount of time to charge for
        :return: energy rate in KwH for charging with the current state of the EnergySource
        """
        pass

