from __future__ import annotations

from typing import NamedTuple, Optional

from hive.model.coordinate import Coordinate
from hive.util.typealiases import *


class Passenger(NamedTuple):
    """
    An immutable class representing a HIVE agent request which is being serviced
    """
    id: PassengerId
    origin: GeoId
    destination: GeoId
    departure_time: int
    vehicle_id: Optional[VehicleId] = None

    def add_vehicle_id(self, vehicle_id: VehicleId) -> Passenger:
        return self._replace(vehicle_id=vehicle_id)


def create_passenger_id(request_id: str, passenger_id: int) -> PassengerId:
    """
    constructs a passenger_id from a request id and a unique id for this passenger
    """
    return f"{request_id}-{passenger_id}"
