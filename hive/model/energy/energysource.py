from __future__ import annotations

from typing import NamedTuple, Optional

from hive.model.energy.energytype import EnergyType
from hive.util.typealiases import PowercurveId
from hive.util.exception import StateOfChargeError, UnitError
from hive.util.units import unit, kw, kwh, Ratio

from copy import copy


class EnergySource(NamedTuple):
    """
    A tuple to represent an energy source. Can be of a unique energy type (i.e. electirc, gasoline, etc)

    :param powercurve_id: The id of the powercurve this energy source will use.
    :type powercurve_id: :py:obj:`PowercurveId`
    :param energy_type: The energy type of this energy source.
    :type energy_type: :py:obj:`EnergySource`
    :param ideal_energy_limit: Refueling is considered complete when this energy limit is reached.
    :type ideal_energy_limit: :py:obj:`kwh`
    :param capacity: The total energy capacity of the energy source.
    :type capacity: :py:obj:`kwh`
    :param energy: The current energy level of the energy source.
    :type energy: :py:obj:`kwh`
    :param max_charge_acceptance_kw: The maximum charge acceptance this energy source can handle (electric only)
    :type max_charge_acceptance_kw: :py:obj:`kw`
    :param charge_threshold: A threshold parameter to allow for some floating point error.
    :type charge_threshold: :py:obj:`kwh`
    """
    powercurve_id: PowercurveId
    energy_type: EnergyType
    ideal_energy_limit: kwh
    capacity: kwh
    energy: kwh
    max_charge_acceptance_kw: kw
    charge_threshold: kwh = 0.001 * unit.kilowatthour
    charge_epsilon: kwh = 0.001 * unit.kilowatthour

    @classmethod
    def build(cls,
              powercurve_id: PowercurveId,
              energy_type: EnergyType,
              capacity: kwh,
              ideal_energy_limit: Optional[kwh] = None,
              max_charge_acceptance_kw: kw = 50 * unit.kilowatt,
              soc: Ratio = 1.0,
              ) -> EnergySource:
        """
        builds an EnergySource for a Vehicle
        :param powercurve_id: the id of the powercurve associated with charging this EnergySource
        :param energy_type: the type of energy used
        :param capacity: the fuel capacity of this EnergySource
        :param ideal_energy_limit: the energy that this EnergySource is limited to based on
        manufacturer requirements and implementation
        :param max_charge_acceptance_kw: the maximum charge power this vehicle can accept
        :param soc: the initial state of charge of this vehicle, in percentage
        :return:
        """
        if not ideal_energy_limit:
            ideal_energy_limit = capacity

        assert 0.0 <= soc <= 1.0, StateOfChargeError(
            f"constructing battery with illegal soc of {(soc * 100.0):.2f}%")
        assert 0.0 <= ideal_energy_limit <= capacity, StateOfChargeError(
            f"max charge acceptance {ideal_energy_limit} needs to be between zero and capacity {capacity} provided")
        assert capacity.units == unit.kilowatthour, UnitError(
            f"expected units of type {unit.kilowatthour}, but got {capacity.units}"
        )
        assert ideal_energy_limit.units == unit.kilowatthour, UnitError(
            f"expected units of type {unit.kilowatthour}, but got {ideal_energy_limit.units}"
        )
        assert max_charge_acceptance_kw.units == unit.kilowatt, UnitError(
            f"expected units of type {unit.kilowatt}, but got {max_charge_acceptance_kw.units}"
        )

        return EnergySource(powercurve_id=powercurve_id,
                            energy_type=energy_type,
                            ideal_energy_limit=ideal_energy_limit,
                            capacity=capacity,
                            energy=capacity * soc,
                            max_charge_acceptance_kw=max_charge_acceptance_kw)

    @property
    def soc(self) -> Ratio:
        """
        calculates the current state of charge as a Ratio

        :return: the SoC (0-1)
        """
        return self.energy.magnitude / self.capacity.magnitude

    def is_at_ideal_energy_limit(self) -> bool:
        """
        True if the EnergySource is at ideal energy limit

        :return: True, if the energy level is equal to or greater than the ideal energy limit,
        within some epsilon, considering that charging curves can prevent reaching this ideal
        value.
        """
        return self.energy.magnitude + self.charge_epsilon.magnitude >= self.ideal_energy_limit.magnitude

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
        return (self.capacity.magnitude - self.charge_threshold.magnitude) < \
            self.energy.magnitude < \
            (self.capacity.magnitude + self.charge_threshold.magnitude)

    def is_empty(self) -> bool:
        """
        True if the EnergySource is empty

        :return: bool
        """
        return self.energy <= 0.0

    def use_energy(self, fuel_used: kwh) -> EnergySource:
        """
        Uses energy and returns the updated energy source

        :param fuel_used: fuel used in kilowatt-hours
        :return: the updated energy source
        """
        # slip out of units to make computation faster
        updated_energy = (self.energy.magnitude - fuel_used.magnitude)
        assert updated_energy >= 0.0, StateOfChargeError("Battery fell below 0% SoC")
        return self._replace(energy=updated_energy * unit.kilowatthour)

    def load_energy(self, fuel_gained: kwh) -> EnergySource:
        """
        adds energy up to the EnergySource's capacity

        :param fuel_gained: the fuel gained for this vehicle due to a refuel event
        :return: the updated EnergySource with fuel added
        """
        updated_energy = min(self.capacity.magnitude, self.energy.magnitude + fuel_gained.magnitude)
        return self._replace(energy=updated_energy * unit.kilowatthour)

    def __repr__(self) -> str:
        soc = self.soc * 100.0
        max_chrg = self.ideal_energy_limit

        return f"Battery({self.energy_type},cap={self.capacity}, max={max_chrg} soc={soc:.2f}%) "

    def copy(self) -> EnergySource:
        return copy(self)
