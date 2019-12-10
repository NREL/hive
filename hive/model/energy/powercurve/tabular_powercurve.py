from typing import TypedDict, Dict, List

import numpy as np

from hive.model.energy.charger import Charger
from hive.model.energy.powercurve.powercurve import Powercurve
from hive.model.energy.energysource import EnergySource
from hive.model.energy.energytype import EnergyType
from hive.util.typealiases import PowercurveId, Time


class TabularPowerCurveInput(TypedDict):
    name: str
    type: str
    power_type: str
    reported_max_charge_acceptance: int
    step_size_seconds: int
    power_curve: List[Dict[float, float]]


class TabularPowercurve(Powercurve):
    """
    builds a tabular, interpolated lookup model from a file
    for energy curves
    """

    def __init__(self, data: TabularPowerCurveInput):
        if 'name' not in data or 'power_type' not in data or 'step_size_seconds' not in data \
                or 'power_curve' not in data or 'reported_max_charge_acceptance' not in data:
            raise IOError("invalid input file for tabular energy curve model")

        self.id = data['name']
        self.energy_type = EnergyType.from_string(data['power_type'])
        self.step_size_seconds = data['step_size_seconds']

        if self.energy_type is None:
            raise AttributeError(f"TabularPowercurve initialized with invalid energy type {self.energy_type}")

        charging_model = sorted(data['power_curve'], key=lambda x: x['soc'])
        normalizing_factor = data['reported_max_charge_acceptance']
        self._charging_soc = np.array(list(map(lambda x: x['soc'], charging_model)))
        self._charging_c_kw = np.array(list(map(lambda x: x['kw'] / normalizing_factor, charging_model)))

    def get_id(self) -> PowercurveId:
        return self.id

    def get_energy_type(self) -> EnergyType:
        return self.energy_type

    def refuel(self,
               energy_source: 'EnergySource',
               charger: 'Charger',
               duration_seconds: Time = 1) -> 'EnergySource':
        """
         (estimated) energy rate due to fueling, based on an interpolated tabular lookup model
         :param energy_source: a vehicle's source of energy
         :param charger: has a capacity scaling effect on the energy_rate
         :param duration_seconds: the amount of time to charge for
         :return: energy rate in KwH for charging with the current state of the EnergySource
         """

        # todo: get feedback about interpretation of v0.2.0 charging logic
        # charging.py line 51:
        # - Q: what is this scaling for?
        # - A: leaf model was annotated with a max charge acceptance of 50.0;
        #      normalizing it to 1 allows us to apply this model to vehicles
        #      with different max charge acceptance values
        # unscaled_df.kw = unscaled_df.kw * battery_kw / 50.0
        # charging.py lines 78-79 (ignored here):
        # - next battery kwh by computing kwh from the kw rate
        # kwh_f = kwh_i + kw / 3600.0
        # - next state of charge percentage
        # soc_f = kwh_f / battery_kwh * 100.0

        # iterate for as many seconds in a time step, by step_size_seconds
        t = 0
        updated_energy = energy_source.copy()
        while t < duration_seconds and updated_energy.not_at_ideal_energy_limit():
            soc = updated_energy.soc * 100  # scaled to [0, 100]

            # charging.py line 76:
            kw_rate = np.interp(soc, self._charging_soc, self._charging_c_kw)
            scaled_kw_rate = kw_rate * energy_source.max_charge_acceptance
            # todo: guessing charger isn't at correct "scale" or "unit" here..
            kwh = scaled_kw_rate * self.step_size_seconds / 3600.0
            charger_limit_kwh = charger.power * self.step_size_seconds / 3600.0
            charger_limited_kwh_rate = min(kwh, charger_limit_kwh)

            updated_energy = updated_energy.load_energy(charger_limited_kwh_rate)
            t += self.step_size_seconds

        return updated_energy
