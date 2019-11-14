from typing import TypedDict, Tuple

from hive.model.request import Request
from hive.model.vehicle import Vehicle
from hive.model.station import Station
from hive.model.base import Base


class AtLocationResponse(TypedDict):
    requests: Tuple[Request, ...]
    vehicles: Tuple[Vehicle, ...]
    stations: Tuple[Station, ...]
    bases: Tuple[Base, ...]
