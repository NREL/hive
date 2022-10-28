from typing import TypeVar

from nrel.hive.model.station.station import Station
from nrel.hive.model.base import Base 
from nrel.hive.model.vehicle.vehicle import Vehicle 
from nrel.hive.model.request import Request 

Entity = TypeVar("Entity", Station, Base, Vehicle, Request)