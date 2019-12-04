from __future__ import annotations

from typing import NamedTuple

from hive.model.energy.energytype import EnergyType
from hive.util.typealiases import KwH, Percentage, PowercurveId
from hive.util.exception import StateOfChargeError

from copy import copy


class EnergySource(NamedTuple):
    """
    a battery has a battery type, capacity and a load
    """
    powercurve_id: PowercurveId
    energy_type: EnergyType
    max_charge_acceptance: KwH
    capacity: KwH
    load: KwH

    @classmethod
    def build(cls,
              powercurve_id: PowercurveId,
              energy_type: EnergyType,
              capacity: KwH,
              max_charge_acceptance: KwH,
              soc: Percentage = 1.0) -> EnergySource:
        """
        builds an EnergySource for a Vehicle
        :param powercurve_id: the id of the powercurve associated with charging this EnergySource
        :param energy_type: the type of energy used
        :param capacity: the fuel capacity of this EnergySource
        :param max_charge_acceptance: the load that this EnergySource is limited to based on
        manufacturer requirements and implementation
        :param soc: the initial state of charge of this vehicle, in percentage
        :return:
        """
        assert 0.0 <= soc <= 1.0, StateOfChargeError(
            f"constructing battery with illegal soc of {(soc * 100.0):.2f}%")
        assert 0.0 <= max_charge_acceptance <= capacity, StateOfChargeError(
            f"max charge acceptance {max_charge_acceptance} needs to be between zero and capacity {capacity} provided")

        return EnergySource(powercurve_id, energy_type, capacity, max_charge_acceptance, capacity * soc)

    @property
    def soc(self) -> Percentage:
        """
        calculates the current state of charge as a Percentage
        :return: the percent SoC
        """
        return self.load / self.capacity

    def is_at_max_charge_aceptance(self) -> bool:
        """
        True if the EnergySource is full of energy
        :return: bool
        """
        return self.load == self.max_charge_acceptance

    def not_at_max_charge_acceptance(self) -> bool:
        """
        True if the EnergySource is not full of energy
        :return: bool
        """
        return self.load < self.max_charge_acceptance

    def is_empty(self) -> bool:
        """
        True if the EnergySource is empty
        :return: bool
        """
        return self.load <= 0.0

    def use_energy(self, fuel_used: KwH) -> EnergySource:
        """

        :param fuel_used:
        :return:
        """
        updated_load = self.load - fuel_used
        assert updated_load >= 0.0, StateOfChargeError("Battery fell below 0% SoC")
        return self._replace(load=updated_load)

    def load_energy(self, fuel_gained: KwH) -> EnergySource:
        """
        adds energy up to the EnergySource's capacity
        :param fuel_gained: the fuel gained for this vehicle due to a charge event
        :return: the updated EnergySource with fuel added
        """
        updated_load = min(self.max_charge_acceptance, self.load + fuel_gained)
        return self._replace(load=updated_load)

    def __repr__(self) -> str:
        soc = self.soc * 100.0
        max_chrg = self.max_charge_acceptance
        return f"Battery({self.energy_type},cap={self.capacity}, max={max_chrg} load={self.load}/{soc:.2f}%) "

    def copy(self) -> EnergySource:
        return copy(self)
