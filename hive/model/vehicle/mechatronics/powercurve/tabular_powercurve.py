from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import yaml
from pkg_resources import resource_string

from hive.model.energy.energytype import EnergyType
from hive.model.vehicle.mechatronics.powercurve.powercurve import Powercurve
from hive.util.units import Seconds, SECONDS_TO_HOURS

if TYPE_CHECKING:
    from hive.util.units import Ratio, KwH, Kw


class TabularPowercurve(Powercurve):
    """
    builds a tabular, interpolated lookup model from a file
    """

    def __init__(self, nominal_max_charge_kw: Kw):
        data = yaml.safe_load(resource_string('hive.resources.vehicles.mechatronics.powercurve', 'normalized.yaml'))

        if 'name' not in data or 'power_type' not in data or 'step_size_seconds' not in data \
                or 'power_curve' not in data or 'reported_max_charge_acceptance_kw' not in data:
            raise IOError("invalid input file for tabular energy curve model")

        self.id = data['name']
        self.energy_type = EnergyType.from_string(data['power_type'])
        self.step_size_seconds = data['step_size_seconds']  # seconds

        if self.energy_type is None:
            raise AttributeError(f"TabularPowercurve initialized with invalid energy type {self.energy_type}")

        charging_model = sorted(data['power_curve'], key=lambda x: x['soc'])
        scale_factor = nominal_max_charge_kw / data['reported_max_charge_acceptance_kw']  # kilowatt
        self._charging_soc = np.array(list(map(lambda x: x['soc'], charging_model)))  # state of charge
        self._charging_rate_kw = np.array(list(map(lambda x: x['kw'], charging_model))) * scale_factor  # kilowatt

    def charge(self,
               start_soc: Ratio,
               energy_limit: KwH,
               power_kw: Kw,
               duration_seconds: Seconds = 1  # seconds
               ) -> KwH:

        """
         (estimated) energy rate due to fueling, based on an interpolated tabular lookup model
         :param start_soc: the starting soc
         :param energy_limit: the cutoff energy limit
         :param power_kw: how fast to charge
         :param duration_seconds: the amount of time to charge for
         :return: the energy source charged for this duration using this charger
         """

        # iterate for as many seconds in a time step, by step_size_seconds
        t = 0
        soc = start_soc * 100  # [scaled to 0, 100]
        energy_kwh = 0
        while t < duration_seconds and not energy_kwh > energy_limit:
            veh_kw_rate = np.interp(soc, self._charging_soc, self._charging_rate_kw)  # kilowatt
            charge_power_kw = min(veh_kw_rate, power_kw)  # kilowatt
            kwh = charge_power_kw * (self.step_size_seconds * SECONDS_TO_HOURS)  # kilowatt-hours

            energy_kwh += kwh

            t += self.step_size_seconds

        return energy_kwh
