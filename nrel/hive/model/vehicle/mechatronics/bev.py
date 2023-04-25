from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, TYPE_CHECKING, Optional, Tuple

import immutables

from nrel.hive.model.energy.energytype import EnergyType
from nrel.hive.model.vehicle.mechatronics.mechatronics_interface import MechatronicsInterface
from nrel.hive.model.vehicle.mechatronics.powercurve import build_powercurve
from nrel.hive.model.vehicle.mechatronics.powertrain import build_powertrain
from nrel.hive.util.typealiases import MechatronicsId
from nrel.hive.util.units import *

if TYPE_CHECKING:
    from nrel.hive.model.energy.charger import Charger
    from nrel.hive.model.vehicle.vehicle import Vehicle
    from nrel.hive.model.roadnetwork.route import Route
    from nrel.hive.model.vehicle.mechatronics.powertrain.powertrain import Powertrain
    from nrel.hive.model.vehicle.mechatronics.powercurve.powercurve import Powercurve

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class BEV(MechatronicsInterface):
    """
    Interface for creating energy sources
    """

    mechatronics_id: MechatronicsId
    battery_capacity_kwh: KwH
    idle_kwh_per_hour: KwH_per_H
    powertrain: Powertrain
    powercurve: Powercurve
    nominal_watt_hour_per_mile: WattHourPerMile
    charge_taper_cutoff_kw: Kw

    battery_full_threshold_kwh: KwH = 0.1

    @classmethod
    def from_dict(
        cls,
        d: Dict[str, str],
        custom_powertrain_constructor: Optional[Callable[[Dict[str, Any]], Powertrain]] = None,
        custom_powercurve_constructor: Optional[Callable[[Dict[str, Any]], Powercurve]] = None,
    ) -> BEV:
        """
        build from a dictionary

        :param d: the dictionary to build from
        :param custom_powertrain_constructor: An optional custom constuctor to build the Powertrain
        :param custom_powercurve_constructor: An optional custom constuctor to build the Powercurve

        :return: the built Mechatronics object
        """
        nominal_watt_hour_per_mile = d["nominal_watt_hour_per_mile"]

        # set scale factor in config dict so the tabular powertrain can use it to scale the normalized lookup
        updated_d = d.copy()
        updated_d["scale_factor"] = nominal_watt_hour_per_mile

        battery_capacity_kwh = float(d["battery_capacity_kwh"])

        if not updated_d.get("powertrain_file"):
            raise FileNotFoundError("missing powertrain file in mechatronics config")
        elif not updated_d.get("powercurve_file"):
            raise FileNotFoundError("missing powercurve file in mechatronics config")

        if custom_powertrain_constructor is None:
            powertrain = build_powertrain(updated_d)
        else:
            powertrain = custom_powertrain_constructor(updated_d)

        if custom_powercurve_constructor is None:
            powercurve = build_powercurve(updated_d)
        else:
            powercurve = custom_powercurve_constructor(updated_d)

        idle_kwh_per_hour = float(updated_d["idle_kwh_per_hour"])
        charge_taper_cutoff_kw = float(updated_d["charge_taper_cutoff_kw"])
        return BEV(
            mechatronics_id=updated_d["mechatronics_id"],
            battery_capacity_kwh=battery_capacity_kwh,
            idle_kwh_per_hour=idle_kwh_per_hour,
            powertrain=powertrain,
            powercurve=powercurve,
            nominal_watt_hour_per_mile=float(nominal_watt_hour_per_mile),
            charge_taper_cutoff_kw=charge_taper_cutoff_kw,
        )

    def valid_charger(self, charger: Charger) -> bool:
        """
        checks to make sure charger is electric energy type

        :param charger: the charger to check
        :return: true/false
        """
        return charger.energy_type == EnergyType.ELECTRIC

    def initial_energy(self, percent_full: Ratio) -> immutables.Map[EnergyType, float]:
        """
        return an energy dictionary from an initial soc

        :param percent_full:
        :return:
        """
        return immutables.Map({EnergyType.ELECTRIC: self.battery_capacity_kwh * percent_full})

    def range_remaining_km(self, vehicle: Vehicle) -> Kilometers:
        """
        how much range remains, in kilometers
        :return:
        """
        energy_kwh = vehicle.energy[EnergyType.ELECTRIC]
        return energy_kwh / (self.nominal_watt_hour_per_mile * WH_TO_KWH) * MILE_TO_KM

    def calc_required_soc(self, required_range: Kilometers) -> Ratio:
        """
        what is the required soc to travel a given distance
        :param required_range: the distance the vehicle needs to travel
        :return:
        """
        required_energy_kwh = (required_range / MILE_TO_KM) * (
            self.nominal_watt_hour_per_mile * WH_TO_KWH
        )
        return required_energy_kwh / self.battery_capacity_kwh

    def fuel_source_soc(self, vehicle: Vehicle) -> Ratio:
        """
        what is the state of charge of the battery
        :return:
        """
        energy_kwh = vehicle.energy[EnergyType.ELECTRIC]
        return energy_kwh / self.battery_capacity_kwh

    def is_empty(self, vehicle: Vehicle) -> bool:
        """
        is the vehicle empty

        :param vehicle:
        :return:
        """
        return vehicle.energy[EnergyType.ELECTRIC] <= 0

    def is_full(self, vehicle: Vehicle) -> bool:
        """
        is the vehicle full

        :param vehicle:
        :return:
        """
        full_kwh = self.battery_capacity_kwh - self.battery_full_threshold_kwh
        return vehicle.energy[EnergyType.ELECTRIC] >= full_kwh

    def consume_energy(self, vehicle: Vehicle, route: Route) -> Vehicle:
        """
        consume_energy over a route


        :param vehicle:

        :param route:
        :return:
        """
        energy_used = self.powertrain.energy_cost(route)
        energy_used_kwh = energy_used * get_unit_conversion(
            self.powertrain.energy_units, Unit.KILOWATT_HOUR
        )
        vehicle_energy_kwh = vehicle.energy[EnergyType.ELECTRIC]
        new_energy_kwh = max(0.0, vehicle_energy_kwh - energy_used_kwh)
        updated_vehicle = vehicle.modify_energy(
            immutables.Map({EnergyType.ELECTRIC: new_energy_kwh})
        )
        updated_vehicle = updated_vehicle.tick_energy_expended(
            immutables.Map({EnergyType.ELECTRIC: vehicle_energy_kwh - new_energy_kwh})
        )
        return updated_vehicle

    def idle(self, vehicle: Vehicle, time_seconds: Seconds) -> Vehicle:
        """
        idle for a set amount of time


        :param vehicle:

        :param time_seconds:
        :return:
        """
        idle_energy_kwh = self.idle_kwh_per_hour * time_seconds * SECONDS_TO_HOURS
        vehicle_energy_kwh = vehicle.energy[EnergyType.ELECTRIC]
        new_energy_kwh = max(0.0, vehicle_energy_kwh - idle_energy_kwh)
        updated_vehicle = vehicle.modify_energy(
            immutables.Map({EnergyType.ELECTRIC: new_energy_kwh})
        )
        updated_vehicle = updated_vehicle.tick_energy_expended(
            immutables.Map({EnergyType.ELECTRIC: vehicle_energy_kwh - new_energy_kwh})
        )

        return updated_vehicle

    def add_energy(
        self, vehicle: Vehicle, charger: Charger, time_seconds: Seconds
    ) -> Tuple[Vehicle, Seconds]:
        """
        add energy into the system


        :param vehicle:

        :param charger:

        :param time_seconds:
        :return: the updated vehicle, along with the time spent charging
        """
        if not self.valid_charger(charger):
            log.warning(
                f"BEV vehicle attempting to use charger of energy type: {charger.energy_type}. Not charging."
            )
            return vehicle, 0

        start_energy_kwh = vehicle.energy[EnergyType.ELECTRIC]

        if charger.rate < self.charge_taper_cutoff_kw:
            charger_energy_kwh = start_energy_kwh + charger.rate * time_seconds * SECONDS_TO_HOURS
            new_energy_kwh = min(self.battery_capacity_kwh, charger_energy_kwh)
            time_charging_seconds = time_seconds
        else:
            # if we're above the charge taper cutoff, we'll use the powercurve
            energy_limit_kwh = self.battery_capacity_kwh - self.battery_full_threshold_kwh
            charger_energy_kwh, time_charging_seconds = self.powercurve.charge(
                start_soc=start_energy_kwh,
                full_soc=energy_limit_kwh,
                power_kw=charger.rate,
                duration_seconds=time_seconds,
            )
            new_energy_kwh = min(self.battery_capacity_kwh, charger_energy_kwh)

        updated_vehicle = vehicle.modify_energy(
            immutables.Map({EnergyType.ELECTRIC: new_energy_kwh})
        )
        updated_vehicle = updated_vehicle.tick_energy_gained(
            immutables.Map({EnergyType.ELECTRIC: new_energy_kwh - start_energy_kwh})
        )

        return updated_vehicle, time_charging_seconds
