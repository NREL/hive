from __future__ import annotations

from copy import copy
from typing import NamedTuple

from hive.model.energy.energytype import EnergyType
from hive.util.exception import StateOfChargeError
from hive.util.typealiases import PowercurveId
from hive.util.units import Kw, KwH, Ratio


class EnergySource(NamedTuple):
    """
    A tuple to represent an energy source. Can be of a unique energy type (i.e. electirc, gasoline, etc)

    :param powercurve_id: The id of the powercurve this energy source will use.
    :type powercurve_id: :py:obj:`PowercurveId`
    :param energy_type: The energy type of this energy source.
    :type energy_type: :py:obj:`EnergySource`
    :param capacity: The total energy capacity of the energy source.
    :type capacity_kwh: :py:obj:`kwh`
    :param energy: The current energy level of the energy source.
    :type energy_kwh: :py:obj:`kwh`
    :param max_charge_acceptance_kw: The maximum charge acceptance this energy source can handle (electric only)
    :type max_charge_acceptance_kw: :py:obj:`kw`
    :param charge_threshold: A threshold parameter to allow for some floating point error.
    :type charge_threshold_kwh: :py:obj:`kwh`
    """
    powercurve_id: PowercurveId
    energy_type: EnergyType
    capacity_kwh: KwH
    energy_kwh: KwH
    max_charge_acceptance_kw: Kw
    charge_threshold_kwh: KwH = 0.01  # kilowatthour

    @classmethod
    def build(cls,
              powercurve_id: PowercurveId,
              energy_type: EnergyType,
              capacity_kwh: KwH,
              max_charge_acceptance_kw: Kw = 50,  # kilowatt
              soc: Ratio = 1.0,
              ) -> EnergySource:
        """
        builds an EnergySource for a Vehicle
        :param powercurve_id: the id of the powercurve associated with charging this EnergySource
        :param energy_type: the type of energy used
        :param capacity_kwh: the fuel capacity of this EnergySource
        :param max_charge_acceptance_kw: the maximum charge power this vehicle can accept
        :param soc: the initial state of charge of this vehicle, in percentage
        :return:
        """
        assert 0.0 <= soc <= 1.0, StateOfChargeError(
            f"constructing battery with illegal soc of {(soc * 100.0):.2f}%")
        assert 0.0 <= capacity_kwh, StateOfChargeError("capacity_kwh must be greater than 0")

        return EnergySource(powercurve_id=powercurve_id,
                            energy_type=energy_type,
                            capacity_kwh=capacity_kwh,
                            energy_kwh=capacity_kwh * soc,
                            max_charge_acceptance_kw=max_charge_acceptance_kw)

    @property
    def soc(self) -> Ratio:
        """
        calculates the current state of charge as a Ratio

        :return: the SoC (0-1)
        """
        return self.energy_kwh / self.capacity_kwh

    def is_full(self) -> bool:
        """
        True if EnergySource is at full capacity

        :return: bool 
        """
        return (self.capacity_kwh - self.charge_threshold_kwh) < \
               self.energy_kwh < (self.capacity_kwh + self.charge_threshold_kwh)

    def is_empty(self) -> bool:
        """
        True if the EnergySource is empty

        :return: bool
        """
        return self.energy_kwh <= 0.0

    def use_energy(self, fuel_used: KwH) -> EnergySource:
        """
        Uses energy and returns the updated energy source

        :param fuel_used: fuel used in kilowatt-hours
        :return: the updated energy source
        """
        # prevent falling below zero units of fuel
        updated_energy = max((self.energy_kwh - fuel_used), 0.0)
        return self._replace(energy_kwh=updated_energy)

    def load_energy(self, fuel_gained_kwh: KwH) -> EnergySource:
        """
        adds energy up to the EnergySource's capacity

        :param fuel_gained_kwh: the fuel gained for this vehicle due to a refuel event
        :return: the updated EnergySource with fuel added
        """
        updated_energy = min(self.capacity_kwh, self.energy_kwh + fuel_gained_kwh)
        return self._replace(energy_kwh=updated_energy)

    def __repr__(self) -> str:
        soc = self.soc * 100.0

        return f"Battery({self.energy_type},cap_kwh={self.capacity_kwh},soc={soc:.2f}%) "

    def copy(self) -> EnergySource:
        return copy(self)
