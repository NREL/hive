from __future__ import annotations

import functools as ft
from typing import NamedTuple, Optional

from hive.model.membership import Membership
from hive.model.sim_time import SimTime
from hive.util.typealiases import *


class Passenger(NamedTuple):
    """
    A tuple representing a passenger in the simulation.
    

    :param id: the unique id of the passenger
    :type id: PassengerId 

    :param origin: the pickup location of the passenger
    :type origin: GeoId 

    :param destination: the destination location of the passenger
    :type destination: GeoId 

    :param departure_time: the departure time of the passenger
    :type departure_time: SimTime

    :param vehicle_id: id of the vehicle that the passenger is occupying
    :type vehicle_id: Optional[VehicleId]
    """
    id: PassengerId
    origin: GeoId
    destination: GeoId
    departure_time: SimTime
    membership: Membership
    vehicle_id: Optional[VehicleId] = None

    def add_vehicle_id(self, vehicle_id: VehicleId) -> Passenger:
        """
        Assign a VehicleId to a passenger


        :param vehicle_id: vehicle id
        :return: updated Passenger
        """
        return self._replace(vehicle_id=vehicle_id)


def create_passenger_id(request_id: RequestId, passenger_id: int) -> PassengerId:
    """
    Constructs a passenger id using a RequestId and an integer


    :param request_id: request id
    :param passenger_id: integer for passenger in a request.
    :rtype: :py:obj:`PassengerId`
    :return: a new unique PassengerId
    """
    return f"{request_id}-{passenger_id}"


def board_vehicle(passengers: Tuple[Passenger, ...], vehicle_id: VehicleId) -> Tuple[Passenger, ...]:
    """
    updates each passenger with a vehicle_id

    :param passengers: the passengers to board
    :param vehicle_id: the vehicle they are boarding
    :return: the passengers with their vehicle_id updated
    """
    return ft.reduce(lambda acc, p: acc + (p.add_vehicle_id(vehicle_id),), passengers, ())
