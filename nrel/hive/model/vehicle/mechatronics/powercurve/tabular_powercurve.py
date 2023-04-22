from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Dict, Tuple, Any

import numpy as np

from nrel.hive.model.energy.energytype import EnergyType
from nrel.hive.model.vehicle.mechatronics.powercurve.powercurve import Powercurve
from nrel.hive.util.units import Seconds, SECONDS_TO_HOURS, Ratio

if TYPE_CHECKING:
    from nrel.hive.util.units import KwH, Kw


class TabularPowercurve(Powercurve):
    """
    builds a tabular, interpolated lookup model from a file
    """

    def __init__(
        self,
        data: Dict[str, Any],
        nominal_max_charge_kw: Optional[Kw] = None,
        battery_capacity_kwh: Optional[KwH] = None,
    ):
        if not nominal_max_charge_kw:
            try:
                nominal_max_charge_kw = float(data["nominal_max_charge_kw"])
            except KeyError:
                raise AttributeError(
                    "Must initialize TabularPowercurve with attribute nominal_max_charge_kw"
                )
        if not battery_capacity_kwh:
            try:
                battery_capacity_kwh = float(data["battery_capacity_kwh"])
            except KeyError:
                raise AttributeError(
                    "Must initialize TabularPowercurve with attribute battery_capacity_kwh"
                )

        expected_keys = [
            "name",
            "power_type",
            "step_size_seconds",
            "power_curve",
        ]
        for key in expected_keys:
            if key not in data:
                raise IOError(
                    f"invalid input file for tabular energy curve model missing key {key}"
                )

        self.id = data["name"]
        self.energy_type = EnergyType.from_string(data["power_type"])
        self.step_size_seconds = data["step_size_seconds"]  # seconds

        if self.energy_type is None:
            raise AttributeError(
                f"TabularPowercurve initialized with invalid energy type {self.energy_type}"
            )

        charging_model = sorted(data["power_curve"], key=lambda x: x["energy_kwh"])
        self._charging_energy_kwh = (
            np.array(list(map(lambda x: x["energy_kwh"], charging_model))) * battery_capacity_kwh
        )
        self._charging_rate_kw = (
            np.array(list(map(lambda x: x["power_kw"], charging_model))) * nominal_max_charge_kw
        )

    def charge(
        self,
        start_soc: Ratio,
        full_soc: Ratio,
        power_kw: Kw,
        duration_seconds: Seconds = 1,  # seconds
    ) -> Tuple[KwH, Seconds]:
        """
        (estimated) energy rate due to fueling, based on an interpolated tabular lookup model

        :param start_soc:
        :param full_soc: the cutoff energy limit
        :param power_kw: how fast to charge
        :param duration_seconds: the amount of time to charge for
        :return: the energy source charged for this duration using this charger_id, along with the time charged
        """

        # iterate for as many seconds in a time step, by step_size_seconds
        t = 0
        energy_kwh = start_soc
        while t < duration_seconds and energy_kwh < full_soc:
            veh_kw_rate = float(
                np.interp(energy_kwh, self._charging_energy_kwh, self._charging_rate_kw)
            )  # kilowatt
            charge_power_kw = min(veh_kw_rate, power_kw)  # kilowatt
            kwh = charge_power_kw * (self.step_size_seconds * SECONDS_TO_HOURS)  # kilowatt-hours

            energy_kwh += kwh

            t += self.step_size_seconds

        return energy_kwh, t
