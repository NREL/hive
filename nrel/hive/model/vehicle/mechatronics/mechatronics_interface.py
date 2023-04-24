from __future__ import annotations

from abc import abstractmethod, ABC
from dataclasses import dataclass
from typing import Dict, TYPE_CHECKING, Tuple

import immutables

from nrel.hive.model.energy import EnergyType

if TYPE_CHECKING:
    from nrel.hive.util.units import Seconds, Ratio, Kilometers
    from nrel.hive.util.typealiases import MechatronicsId
    from nrel.hive.model.energy.charger import Charger
    from nrel.hive.model.vehicle.vehicle import Vehicle
    from nrel.hive.model.roadnetwork.route import Route


@dataclass(frozen=True)
class MechatronicsMixin:
    mechatronics_id: MechatronicsId


class MechatronicsInterfaceABC(ABC):
    """
    Interface for creating energy sources
    """

    @classmethod
    @abstractmethod
    def from_dict(cls, d: Dict[str, str]) -> MechatronicsInterface:
        """
        build from a dictionary

        :param d: the dictionary to build from
        :return: the built Mechatronics object
        """

    @abstractmethod
    def valid_charger(self, charger: Charger) -> bool:
        """
        check to see if the mechatronics instance can use a certain charger

        :param charger: the charger to check
        :return: true/false
        """

    @abstractmethod
    def initial_energy(self, percent_full: Ratio) -> immutables.Map[EnergyType, float]:
        """
        construct an initial energy state for a Vehicle

        :param percent_full: the amount of energy in the vehicle
        :return: the Vehicle.energy at startup
        """

    @abstractmethod
    def range_remaining_km(self, vehicle: Vehicle) -> Kilometers:
        """
        how much range remains, in kilometers
        :return:
        """

    @abstractmethod
    def calc_required_soc(self, required_range: Kilometers) -> Ratio:
        """
        How much SOC needed to go required_range
        """

    @abstractmethod
    def fuel_source_soc(self, vehicle: Vehicle) -> Ratio:
        """
        how much battery soc
        :return:
        """

    @abstractmethod
    def is_empty(self, vehicle: Vehicle) -> bool:
        """
        can the vehicle still move?
        :return:
        """

    @abstractmethod
    def is_full(self, vehicle: Vehicle) -> bool:
        """
        is the vehicle full of energy?
        :return:
        """

    @abstractmethod
    def consume_energy(self, vehicle: Vehicle, route: Route) -> Vehicle:
        """
        consume energy over a route

        :param vehicle:
        :param route:
        :return: the vehicle after moving;
        """

    @abstractmethod
    def idle(self, vehicle: Vehicle, time_seconds: Seconds) -> Vehicle:
        """
        idle for a set amount of time


        :param vehicle:
        :param time_seconds:
        :return:
        """

    @abstractmethod
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


class MechatronicsInterface(MechatronicsMixin, MechatronicsInterfaceABC):
    """"""
