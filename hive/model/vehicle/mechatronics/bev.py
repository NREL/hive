from __future__ import annotations

from typing import Dict, NamedTuple, TYPE_CHECKING

from hive.model.energy.energytype import EnergyType
from hive.model.roadnetwork.route import route_distance_km
from hive.model.vehicle.mechatronics.interface import MechatronicsInterface
from hive.util.units import Kilometers, Seconds, KwH, KwH_per_H, Ratio, WH_TO_KWH, SECONDS_TO_HOURS

if TYPE_CHECKING:
    from hive.model.energy.charger import Charger
    from hive.model.vehicle.vehicle import Vehicle
    from hive.model.roadnetwork.route import Route


class BEV(NamedTuple, MechatronicsInterface):
    """
    Interface for creating energy sources
    """
    battery_capacity_kwh: KwH = 50
    watt_hour_per_km: Kilometers = 150
    idle_kwh_per_hour: KwH_per_H = 0.8

    @classmethod
    def from_dict(cls, d: Dict[str, str]) -> BEV:
        """
        build from a dictionary
        :param d: the dictionary to build from
        :return: the built Mechatronics object
        """
        return BEV()

    def initial_energy(self, battery_soc: Ratio) -> Dict[EnergyType, float]:
        """
        return an energy dictionary from an initial soc
        :param battery_soc:
        :return:
        """
        return {EnergyType.ELECTRIC: self.battery_capacity_kwh * battery_soc}

    def range_remaining_km(self, vehicle: Vehicle) -> Kilometers:
        """
        how much range remains, in miles
        :return:
        """
        energy_kwh = vehicle.energy[EnergyType.ELECTRIC]
        return energy_kwh / (self.watt_hour_per_km * WH_TO_KWH)

    def battery_soc(self, vehicle: Vehicle) -> Ratio:
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
        return vehicle.energy[EnergyType.ELECTRIC] >= self.battery_capacity_kwh

    def move(self, vehicle: Vehicle, route: Route) -> Vehicle:
        """
        move over a set distance

        :param vehicle:
        :param route:
        :return:
        """
        energy_used_kwh = route_distance_km(route) * self.watt_hour_per_km * WH_TO_KWH
        vehicle_energy_kwh = vehicle.energy[EnergyType.ELECTRIC]
        new_energy_kwh = max(0, vehicle_energy_kwh - energy_used_kwh)
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
        new_energy_kwh = max(0, vehicle_energy_kwh - idle_energy_kwh)
        updated_vehicle = vehicle.modify_energy({EnergyType.ELECTRIC: new_energy_kwh})

        return updated_vehicle

    def add_energy(self, vehicle: Vehicle, charger: Charger, time_seconds: Seconds) -> Vehicle:
        """
        add energy into the system

        :param vehicle:
        :param charger:
        :param time_seconds:
        :return:
        """
        charger_energy_kwh = charger.power_kw * time_seconds * SECONDS_TO_HOURS
        vehicle_energy_kwh = vehicle.energy[EnergyType.ELECTRIC]
        new_energy_kwh = min(self.battery_capacity_kwh, vehicle_energy_kwh + charger_energy_kwh)
        updated_vehicle = vehicle.modify_energy({EnergyType.ELECTRIC: new_energy_kwh})

        return updated_vehicle
