from __future__ import annotations

from abc import abstractmethod
from typing import Dict, TYPE_CHECKING

from hive.util.abc_named_tuple_meta import ABCNamedTupleMeta

if TYPE_CHECKING:
    from hive.util.units import Seconds, Ratio, Kilometers
    from hive.util.typealiases import MechatronicsId
    from hive.model.energy.charger import Charger
    from hive.model.vehicle.vehicle import Vehicle
    from hive.model.roadnetwork.route import Route


class MechatronicsInterface(metaclass=ABCNamedTupleMeta):
    """
    Interface for creating energy sources
    """

    @property
    @abstractmethod
    def mechatronics_id(self) -> MechatronicsId:
        """
        what id?
        :return:
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
    def range_remaining_km(self, vehicle: Vehicle) -> Kilometers:
        """
        how much range remains, in kilometers
        :return:
        """

    @abstractmethod
    def battery_soc(self, vehicle: Vehicle) -> Ratio:
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
    def move(self, vehicle: Vehicle, route: Route) -> Vehicle:
        """
        move over a set distance

        :param vehicle:
        :param route:
        :return:
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
    def add_energy(self, vehicle: Vehicle, charger: Charger, time_seconds: Seconds) -> Vehicle:
        """
        add energy into the system

        :param vehicle:
        :param charger:
        :param time_seconds:
        :return:
        """