from __future__ import annotations

from typing import NamedTuple, Optional

from hive.model.energy.energytype import EnergyType
from hive.util.typealiases import PowercurveId
from hive.util.exception import StateOfChargeError, UnitError
from hive.util.units import unit, kw, kwh, Ratio

from copy import copy


class EnergySource(NamedTuple):
    """
    a battery has a battery type, capacity and a energy
    """
    powercurve_id: PowercurveId
    energy_type: EnergyType
    ideal_energy_limit: kwh
    capacity: kwh
    energy: kwh
    max_charge_acceptance_kw: kw
    charge_threshold: kwh = 0.001 * unit.kilowatthour

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

        return EnergySource(powercurve_id,
                            energy_type,
                            capacity,
                            ideal_energy_limit,
                            capacity * soc,
                            max_charge_acceptance_kw)

    @property
    def soc(self) -> Ratio:
        """
        calculates the current state of charge as a Percentage
        :return: the percent SoC
        """
        return self.energy / self.capacity

    def is_at_ideal_energy_limit(self) -> bool:

        """
        True if the EnergySource is at ideal energy limit 
        :return: bool
        """
        return self.energy >= self.ideal_energy_limit


    def not_at_ideal_energy_limit(self) -> bool:
        """
        True if the EnergySource is not at ideal energy limit 
        :return: bool
        """
        return self.energy < self.ideal_energy_limit

    def is_full(self) -> bool:
        """
        True if EnergySource is full
        :return: bool 
        """
        return (self.capacity - self.charge_threshold) < self.energy < (self.capacity + self.charge_threshold)

    def is_empty(self) -> bool:
        """
        True if the EnergySource is empty
        :return: bool
        """
        return self.energy <= 0.0

    def use_energy(self, fuel_used: kwh) -> EnergySource:
        """

        :param fuel_used:
        :return:
        """
        updated_energy = self.energy - fuel_used
        assert updated_energy >= 0.0, StateOfChargeError("Battery fell below 0% SoC")
        return self._replace(energy=updated_energy)

    def load_energy(self, fuel_gained: kwh) -> EnergySource:
        """
        adds energy up to the EnergySource's capacity
        :param fuel_gained: the fuel gained for this vehicle due to a charge event
        :return: the updated EnergySource with fuel added
        """
        updated_energy = min(self.capacity, self.energy + fuel_gained)
        return self._replace(energy=updated_energy)

    def __repr__(self) -> str:
        soc = self.soc * 100.0
        max_chrg = self.ideal_energy_limit

        return f"Battery({self.energy_type},cap={self.capacity}, max={max_chrg} soc={soc:.2f}%) "

    def copy(self) -> EnergySource:
        return copy(self)
