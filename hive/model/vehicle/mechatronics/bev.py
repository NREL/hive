from __future__ import annotations

from typing import Dict, NamedTuple, TYPE_CHECKING, Tuple

from hive.model.energy.energytype import EnergyType
from hive.model.vehicle.mechatronics.mechatronics_interface import MechatronicsInterface
from hive.model.vehicle.mechatronics.powercurve import build_powercurve
from hive.model.vehicle.mechatronics.powertrain import build_powertrain
from hive.util.typealiases import MechatronicsId
from hive.util.units import *

if TYPE_CHECKING:
    from hive.model.energy.charger import Charger
    from hive.model.vehicle.vehicle import Vehicle
    from hive.model.roadnetwork.route import Route
    from hive.model.vehicle.mechatronics.powertrain.powertrain import Powertrain
    from hive.model.vehicle.mechatronics.powercurve.powercurve import Powercurve


class BEV(NamedTuple, MechatronicsInterface):
    """
    Interface for creating energy sources
    """

    mechatronics_id: MechatronicsId
    battery_capacity_kwh: KwH
    idle_kwh_per_hour: KwH_per_H
    powertrain: Powertrain
    powercurve:  Powercurve
    nominal_watt_hour_per_mile: WattHourPerMile
    charge_taper_cutoff_kw: Kw

    battery_full_threshold_kwh: KwH = 0.1

    @classmethod
    def from_dict(cls, d: Dict[str, str]) -> BEV:
        """
        build from a dictionary
        :param d: the dictionary to build from
        :return: the built Mechatronics object
        """
        nominal_watt_hour_per_mile = float(d['nominal_watt_hour_per_mile'])
        battery_capacity_kwh = float(d['battery_capacity_kwh'])
        powertrain = build_powertrain(d)
        powercurve = build_powercurve(d)
        idle_kwh_per_hour = float(d['idle_kwh_per_hour'])
        charge_taper_cutoff_kw = float(d['charge_taper_cutoff_kw'])
        return BEV(
            mechatronics_id=d['mechatronics_id'],
            battery_capacity_kwh=battery_capacity_kwh,
            idle_kwh_per_hour=idle_kwh_per_hour,
            powertrain=powertrain,
            powercurve=powercurve,
            nominal_watt_hour_per_mile=nominal_watt_hour_per_mile,
            charge_taper_cutoff_kw=charge_taper_cutoff_kw
        )

    def valid_charger(self, charger: Charger) -> bool:
        """
        checks to make sure charger is electric energy type
        :param charger: the charger to check
        :return: true/false
        """
        return charger.energy_type == EnergyType.ELECTRIC

    def initial_energy(self, percent_full: Ratio) -> Dict[EnergyType, float]:
        """
        return an energy dictionary from an initial soc
        :param percent_full:
        :return:
        """
        return {EnergyType.ELECTRIC: self.battery_capacity_kwh * percent_full}

    def range_remaining_km(self, vehicle: Vehicle) -> Kilometers:
        """
        how much range remains, in kilometers
        :return:
        """
        energy_kwh = vehicle.energy[EnergyType.ELECTRIC]
        return energy_kwh / (self.nominal_watt_hour_per_mile * WH_TO_KWH) * MILE_TO_KM

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

    def move(self, vehicle: Vehicle, route: Route) -> Vehicle:
        """
        move over a set distance

        :param vehicle:
        :param route:
        :return:
        """
        energy_used_kwh = self.powertrain.energy_cost(route)
        vehicle_energy_kwh = vehicle.energy[EnergyType.ELECTRIC]
        new_energy_kwh = max(0.0, vehicle_energy_kwh - energy_used_kwh)
        updated_vehicle = vehicle.modify_energy({EnergyType.ELECTRIC: new_energy_kwh})

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
        updated_vehicle = vehicle.modify_energy({EnergyType.ELECTRIC: new_energy_kwh})

        return updated_vehicle

    def add_energy(self, vehicle: Vehicle, charger: Charger, time_seconds: Seconds) -> Tuple[Vehicle, Seconds]:
        """
        add energy into the system

        :param vehicle:
        :param charger:
        :param time_seconds:
        :return: the updated vehicle, along with the time spent charging
        """
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

        updated_vehicle = vehicle.modify_energy({EnergyType.ELECTRIC: new_energy_kwh})

        return updated_vehicle, time_charging_seconds
