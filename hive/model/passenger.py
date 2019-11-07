from typing import NamedTuple

from hive.model.coordinate import Coordinate
from hive.util.typealiases import *


class Passenger(NamedTuple):
    """
    An immutable class representing a HIVE agent request which is being serviced
    """
    id: PassengerId
    origin: Coordinate
    destination: Coordinate
    departure_time: int
    vehicle_id: VehicleId


def create_passenger_id(request_id: str, passenger_id: int) -> PassengerId:
    """
    constructs a passenger_id from a request id and a unique id for this passenger
    """
    return f"{request_id}-{passenger_id}"
