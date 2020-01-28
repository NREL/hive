from __future__ import annotations

from typing import TypedDict, Dict, List, TYPE_CHECKING

import numpy as np

from hive.model.energy.powercurve.powercurve import Powercurve
from hive.model.energy.energytype import EnergyType
from hive.util.units import Seconds, SECONDS_TO_HOURS
from hive.util.typealiases import PowercurveId

if TYPE_CHECKING:
    from hive.model.energy.charger import Charger
    from hive.model.energy.energysource import EnergySource


class TabularPowerCurveInput(TypedDict):
    """
    Inputs for the TabularPowerCurve
    """
    name: str
    type: str
    power_type: str
    reported_max_charge_acceptance_kw: int
    step_size_seconds: Seconds
    power_curve: List[Dict[float, float]]


class TabularPowercurve(Powercurve):
    """
    builds a tabular, interpolated lookup model from a file
    """

    def __init__(self, data: TabularPowerCurveInput):
        if 'name' not in data or 'power_type' not in data or 'step_size_seconds' not in data \
                or 'power_curve' not in data or 'reported_max_charge_acceptance_kw' not in data:
            raise IOError("invalid input file for tabular energy curve model")

        self.id = data['name']
        self.energy_type = EnergyType.from_string(data['power_type'])
        self.step_size_seconds = data['step_size_seconds']  # seconds

        if self.energy_type is None:
            raise AttributeError(f"TabularPowercurve initialized with invalid energy type {self.energy_type}")

        charging_model = sorted(data['power_curve'], key=lambda x: x['soc'])
        self.max_charge_acceptance_kw = data['reported_max_charge_acceptance_kw']  # kilowatt
        self._charging_soc = np.array(list(map(lambda x: x['soc'], charging_model)))  # state of charge
        self._charging_rate_kw = np.array(list(map(lambda x: x['kw'], charging_model)))  # kilowatt

    def get_id(self) -> PowercurveId:
        return self.id

    def get_energy_type(self) -> EnergyType:
        return self.energy_type

    def refuel(self,
               energy_source: EnergySource,
               charger: Charger,
               duration_seconds: Seconds = 1  # seconds
               ) -> EnergySource:

        """
         (estimated) energy rate due to fueling, based on an interpolated tabular lookup model
         :param energy_source: a vehicle's source of energy
         :param charger: has a capacity scaling effect on the energy_rate
         :param duration_seconds: the amount of time to charge for
         :return: the energy source charged for this duration using this charger
         """

        # iterate for as many seconds in a time step, by step_size_seconds
        t = 0
        updated_energy = energy_source.copy()
        scale_factor = energy_source.max_charge_acceptance_kw / self.max_charge_acceptance_kw
        while t < duration_seconds and updated_energy.not_at_ideal_energy_limit():
            soc = updated_energy.soc * 100  # scaled to [0, 100]

            veh_kw_rate = np.interp(soc, self._charging_soc, self._charging_rate_kw) * scale_factor  # kilowatt
            charge_power_kw = min(veh_kw_rate, charger.power_kw)  # kilowatt
            kwh = charge_power_kw * (self.step_size_seconds * SECONDS_TO_HOURS)  # kilowatt-hours

            updated_energy = updated_energy.load_energy(kwh)

            t += self.step_size_seconds

        return updated_energy
