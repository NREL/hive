from __future__ import annotations
from typing import List, Tuple, TypedDict, NamedTuple
import h3
from nrel.hive.model.sim_time import SimTime
from nrel.hive.util.typealiases import VehicleId, GeoId


class Property(TypedDict):
    vehicle_id: VehicleId
    vehicle_state: str
    start_time: int


class Coord(NamedTuple):
    lon: float
    lat: float
    z: float
    timestamp: int


class Geometry(TypedDict):
    type: str
    coordinates: list[Coord]


class Feature(TypedDict):
    type: str
    properties: Property
    geometry: Geometry


class KeplerFeature:
    def __init__(self, id: VehicleId, state: str, starttime: SimTime) -> None:
        """
        Creates a new reusable Feature for Kepler json files.

        :param id: The VehicleId of the vehicle
        :param state: The string value of the vehicle's state during creation
        :param starttime: The SimTime object of when the vehicle was recorded to start the trip
        """
        self.id: VehicleId = id
        self.state: str = state
        self.starttime: SimTime = starttime
        self.coords: List[Tuple[GeoId, SimTime]] = []

    def add_coord(self, geoid: GeoId, timestamp: SimTime) -> None:
        """
        Adds a coordinate to the Vehicles list of coordinates while on the current trip

        :param geoid: H3 cell
        :param timestamp: The time when the vehicle was recorded at the geoid

        :return: None
        """
        self.coords.append((geoid, timestamp))

    def gen_json(self) -> Feature:
        """
        Generates a json freindly dictionary for Kepler on the vehicle's trip

        :return: A dictionary on the vehicle's trip for Kepler
        """
        log_dict: Feature = {
            "type": "Feature",
            "properties": {
                "vehicle_id": self.id,
                "vehicle_state": self.state,
                "start_time": self.starttime.as_epoch_time(),
            },
            "geometry": {"type": "LineString", "coordinates": []},
        }
        for geoid, timestamp in self.coords:
            lat, lon = h3.h3_to_geo(geoid)
            assert isinstance(lat, float)
            assert isinstance(lon, float)
            log_dict["geometry"]["coordinates"].append(
                Coord(lon, lat, 0, timestamp.as_epoch_time())
            )

        return log_dict

    def reset(self, state: str, starttime: SimTime) -> None:
        """
        Resets the vehicle's coordinate list so that the vehicle can start a new trip

        :param state: The string value of the vehicle's state
        :param starttime: The SimTime object of when the vehicle was recorded to start the trip

        :return: None
        """
        self.coords.clear()
        self.state = state
        self.starttime = starttime
