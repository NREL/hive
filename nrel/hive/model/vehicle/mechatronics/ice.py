from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, TYPE_CHECKING, Optional, Tuple

import immutables

from nrel.hive.model.energy.energytype import EnergyType
from nrel.hive.model.vehicle.mechatronics.mechatronics_interface import MechatronicsInterface
from nrel.hive.model.vehicle.mechatronics.powertrain import build_powertrain
from nrel.hive.util.typealiases import MechatronicsId
from nrel.hive.util.units import *

if TYPE_CHECKING:
    from nrel.hive.model.energy.charger.charger import Charger
    from nrel.hive.model.vehicle.vehicle import Vehicle
    from nrel.hive.model.roadnetwork.route import Route
    from nrel.hive.model.vehicle.mechatronics.powertrain.powertrain import Powertrain

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class ICE(MechatronicsInterface):
    """
    Mechatronics for an internal combustion engine (ICE)
    """

    mechatronics_id: MechatronicsId
    tank_capacity_gallons: GallonGasoline
    idle_gallons_per_hour: GallonPerHour
    powertrain: Powertrain
    nominal_miles_per_gallon: MilesPerGallon

    @classmethod
    def from_dict(
        cls,
        d: Dict,
        custom_powertrain_constructor: Optional[Callable[[Dict[str, Any]], Powertrain]] = None,
    ) -> ICE:
        """
        build from a dictionary

        :param d: the dictionary to build from
        :return: the built Mechatronics object
        """
        tank_capacity_gallons = float(d["tank_capacity_gallons"])
        idle_gallons_per_hour = float(d["idle_gallons_per_hour"])
        nominal_miles_per_gallon = float(d["nominal_miles_per_gallon"])

        # set scale factor in config dict so the tabular powertrain can use it to scale the normalized lookup
        updated_d = d.copy()
        updated_d["scale_factor"] = 1 / nominal_miles_per_gallon

        if custom_powertrain_constructor is None:
            powertrain = build_powertrain(updated_d)
        else:
            powertrain = custom_powertrain_constructor(updated_d)

        return ICE(
            mechatronics_id=updated_d["mechatronics_id"],
            tank_capacity_gallons=tank_capacity_gallons,
            idle_gallons_per_hour=idle_gallons_per_hour,
            powertrain=powertrain,
            nominal_miles_per_gallon=nominal_miles_per_gallon,
        )

    def valid_charger(self, charger: Charger) -> bool:
        """
        checks to make sure charger is gasoline energy type


        :param charger: the charger to check
        :return: true/false
        """
        return charger.energy_type == EnergyType.GASOLINE

    def initial_energy(self, percent_full: Ratio) -> immutables.Map[EnergyType, float]:
        """
        return an energy dictionary from an initial soc

        :param percent_full:
        :return:
        """
        return immutables.Map({EnergyType.GASOLINE: self.tank_capacity_gallons * percent_full})

    def range_remaining_km(self, vehicle: Vehicle) -> Kilometers:
        """
        how much range remains, in kilometers
        :return:
        """
        energy_gal_gas = vehicle.energy[EnergyType.GASOLINE]
        miles = energy_gal_gas * self.nominal_miles_per_gallon
        km = miles * MILE_TO_KM
        return km

    def calc_required_soc(self, required_range: Kilometers) -> Ratio:
        """
        what is the required tank capacity to travel a given distance
        :param required_range: the distance the vehicle needs to travel
        :return:
        """
        miles = required_range / MILE_TO_KM
        required_energy_gal_gas = miles / self.nominal_miles_per_gallon
        return required_energy_gal_gas / self.tank_capacity_gallons

    def fuel_source_soc(self, vehicle: Vehicle) -> Ratio:
        """
        what is the level of the fuel tank
        :return:
        """
        energy_gal_gas = vehicle.energy[EnergyType.GASOLINE]
        return energy_gal_gas / self.tank_capacity_gallons

    def is_empty(self, vehicle: Vehicle) -> bool:
        """
        is the vehicle empty

        :param vehicle:
        :return:
        """
        return vehicle.energy[EnergyType.GASOLINE] <= 0

    def is_full(self, vehicle: Vehicle) -> bool:
        """
        is the vehicle full

        :param vehicle:
        :return:
        """
        return vehicle.energy[EnergyType.GASOLINE] >= self.tank_capacity_gallons

    def consume_energy(self, vehicle: Vehicle, route: Route) -> Vehicle:
        """
        consume energy over a route

        :param vehicle:

        :param route:
        :return:
        """
        energy_used = self.powertrain.energy_cost(route)
        energy_used_gal_gas = energy_used * get_unit_conversion(
            self.powertrain.energy_units, Unit.GALLON_GASOLINE
        )

        vehicle_energy_gal_gas = vehicle.energy[EnergyType.GASOLINE]
        new_energy_gal_gas = max(0.0, vehicle_energy_gal_gas - energy_used_gal_gas)
        updated_vehicle = vehicle.modify_energy(
            immutables.Map({EnergyType.GASOLINE: new_energy_gal_gas})
        )
        updated_vehicle = vehicle.tick_energy_expended(
            immutables.Map({EnergyType.GASOLINE: vehicle_energy_gal_gas - new_energy_gal_gas})
        )
        return updated_vehicle

    def idle(self, vehicle: Vehicle, time_seconds: Seconds) -> Vehicle:
        """
        idle for a set amount of time


        :param vehicle:

        :param time_seconds:
        :return:
        """
        idle_energy_gal_gas = self.idle_gallons_per_hour * time_seconds * SECONDS_TO_HOURS
        vehicle_energy_gal_gas = vehicle.energy[EnergyType.GASOLINE]
        new_energy_gal_gas = max(0.0, vehicle_energy_gal_gas - idle_energy_gal_gas)
        updated_vehicle = vehicle.modify_energy(
            immutables.Map({EnergyType.GASOLINE: new_energy_gal_gas})
        )
        updated_vehicle = vehicle.tick_energy_expended(
            immutables.Map({EnergyType.GASOLINE: vehicle_energy_gal_gas - new_energy_gal_gas})
        )

        return updated_vehicle

    def add_energy(
        self, vehicle: Vehicle, charger: Charger, time_seconds: Seconds
    ) -> Tuple[Vehicle, Seconds]:
        """
        add energy into the system. units for the charger are gallons per second


        :param vehicle:

        :param charger:

        :param time_seconds:
        :return: the updated vehicle, along with the time spent charging
        """
        if not self.valid_charger(charger):
            log.warning(
                f"ICE vehicle attempting to use charger of energy type: {charger.energy_type}. Not charging."
            )
            return vehicle, 0
        start_gal_gas = vehicle.energy[EnergyType.GASOLINE]

        pump_gal_gas = start_gal_gas + charger.rate * time_seconds
        new_gal_gas = min(self.tank_capacity_gallons, pump_gal_gas)

        updated_vehicle = vehicle.modify_energy(immutables.Map({EnergyType.GASOLINE: new_gal_gas}))
        updated_vehicle = updated_vehicle.tick_energy_gained(
            immutables.Map({EnergyType.GASOLINE: new_gal_gas - start_gal_gas})
        )

        return updated_vehicle, time_seconds
