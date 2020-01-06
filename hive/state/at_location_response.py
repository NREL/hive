from typing import TypedDict, Tuple

from hive.model.request import Request
from hive.model.vehicle import Vehicle
from hive.model.station import Station
from hive.model.base import Base


class AtLocationResponse(TypedDict):
    """
    Wrapper for entities at a specific location.
    
    :param requests: requests at the location
    :type requests: :py:obj:`Tuple[Request, ...]` 
    :param vehicles: vehicles at the location
    :type vehicles: :py:obj:`Tuple[Request, ...]` 
    :param stations: stations at the location
    :type stations: :py:obj:`Tuple[Stations, ...]` 
    :param bases: bases at the location
    :type bases: :py:obj:`Tuple[Base, ...]`
    """
    requests: Tuple[Request, ...]
    vehicles: Tuple[Vehicle, ...]
    stations: Tuple[Station, ...]
    bases: Tuple[Base, ...]
