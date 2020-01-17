from __future__ import annotations

from typing import NamedTuple, Optional
from copy import copy

from hive.model.energy.energytype import EnergyType
from hive.util.typealiases import PowercurveId
from hive.util.exception import StateOfChargeError
from hive.util.units import kw, kwh, Ratio


class EnergySource(NamedTuple):
    """
    A tuple to represent an energy source. Can be of a unique energy type (i.e. electirc, gasoline, etc)

    :param powercurve_id: The id of the powercurve this energy source will use.
    :type powercurve_id: :py:obj:`PowercurveId`
    :param energy_type: The energy type of this energy source.
    :type energy_type: :py:obj:`EnergySource`
    :param ideal_energy_limit: Refueling is considered complete when this energy limit is reached.
    :type ideal_energy_limit_kwh: :py:obj:`kwh`
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
    ideal_energy_limit_kwh: kwh
    capacity_kwh: kwh
    energy_kwh: kwh
    max_charge_acceptance_kw: kw
    charge_threshold_kwh: kwh = 0.001  # kilowatthour

    @classmethod
    def build(cls,
              powercurve_id: PowercurveId,
              energy_type: EnergyType,
              capacity_kwh: kwh,
              ideal_energy_limit_kwh: Optional[kwh] = None,
              max_charge_acceptance_kw: kw = 50,  # kilowatt
              soc: Ratio = 1.0,
              ) -> EnergySource:
        """
        builds an EnergySource for a Vehicle
        :param powercurve_id: the id of the powercurve associated with charging this EnergySource
        :param energy_type: the type of energy used
        :param capacity_kwh: the fuel capacity of this EnergySource
        :param ideal_energy_limit_kwh: the energy that this EnergySource is limited to based on
        manufacturer requirements and implementation
        :param max_charge_acceptance_kw: the maximum charge power this vehicle can accept
        :param soc: the initial state of charge of this vehicle, in percentage
        :return:
        """
        if not ideal_energy_limit_kwh:
            ideal_energy_limit_kwh = capacity_kwh

        assert 0.0 <= soc <= 1.0, StateOfChargeError(
            f"constructing battery with illegal soc of {(soc * 100.0):.2f}%")
        assert 0.0 <= ideal_energy_limit_kwh <= capacity_kwh, StateOfChargeError(
            f"max charge acceptance {ideal_energy_limit_kwh} needs to be between \
            zero and capacity {capacity_kwh} provided")

        return EnergySource(powercurve_id=powercurve_id,
                            energy_type=energy_type,
                            ideal_energy_limit_kwh=ideal_energy_limit_kwh,
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

    def is_at_ideal_energy_limit(self) -> bool:
        """
        True if the EnergySource is at ideal energy limit

        :return: True, if the energy level is equal to or greater than the ideal energy limit,
        within some epsilon, considering that charging curves can prevent reaching this ideal
        value.
        """
        return self.energy_kwh + self.charge_threshold_kwh >= self.ideal_energy_limit_kwh

    def not_at_ideal_energy_limit(self) -> bool:
        """
        True if the EnergySource is not at ideal energy limit

        :return: bool
        """
        return not self.is_at_ideal_energy_limit()

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

    def use_energy(self, fuel_used: kwh) -> EnergySource:
        """
        Uses energy and returns the updated energy source

        :param fuel_used: fuel used in kilowatt-hours
        :return: the updated energy source
        """
        # slip out of units to make computation faster
        updated_energy = (self.energy_kwh - fuel_used)
        assert updated_energy >= 0.0, StateOfChargeError("Battery fell below 0% SoC")
        return self._replace(energy_kwh=updated_energy)

    def load_energy(self, fuel_gained_kwh: kwh) -> EnergySource:
        """
        adds energy up to the EnergySource's capacity

        :param fuel_gained_kwh: the fuel gained for this vehicle due to a refuel event
        :return: the updated EnergySource with fuel added
        """
        updated_energy = min(self.capacity_kwh, self.energy_kwh + fuel_gained_kwh)
        return self._replace(energy_kwh=updated_energy)

    def __repr__(self) -> str:
        soc = self.soc * 100.0
        max_chrg = self.ideal_energy_limit_kwh

        return f"Battery({self.energy_type},cap_kwh={self.capacity_kwh}, max_kwh={max_chrg} soc={soc:.2f}%) "

    def copy(self) -> EnergySource:
        return copy(self)
