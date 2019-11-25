from math import sqrt, pow
from typing import NamedTuple

from h3 import h3
from haversine import haversine

from hive.util.typealiases import *


class Coordinate(NamedTuple):
    """
    a latitude (y) and longitude (x) tuple
    """
    lat: float
    lon: float


def geoid_to_coordinate(geoid: GeoId) -> Coordinate:
    coord = h3.h3_to_geo(geoid)
    return Coordinate(coord[0], coord[1])


def coordinate_to_geoid(coordinate: Coordinate, resolution: int) -> GeoId:
    geoid = h3.geo_to_h3(coordinate.lat, coordinate.lon, resolution)
    return geoid


def dist_euclidian(a: Coordinate, b: Coordinate) -> float:
    return sqrt(pow((a.lat - b.lat), 2) + pow((a.lon - b.lon), 2))


def dist_haversine(a: Coordinate, b: Coordinate) -> Km:
    return haversine(a, b)


def dist_geoid_haversine(a: GeoId, b: GeoId) -> Km:
    a_coord = geoid_to_coordinate(a)
    b_coord = geoid_to_coordinate(b)
    return haversine(a_coord, b_coord)


def interpolate_between_coordinates(a: Coordinate, b: Coordinate, percent: Percentage) -> Coordinate:
    # TODO: Right now this is just a linear interpolation. Do we want/need a more accurate interpolation?
    lat = a.lat + (b.lat - a.lat) * percent
    lon = a.lon + (b.lon - a.lon) * percent
    return Coordinate(lat, lon)
