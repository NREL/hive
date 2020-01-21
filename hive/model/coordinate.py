from math import sqrt, pow
from typing import NamedTuple

from h3 import h3
from haversine import haversine

from hive.util.typealiases import *
from hive.util.units import Kilometers, Ratio


class Coordinate(NamedTuple):
    """
    A tuple holding latitude and longitude information.

    :param lat: Latitude of coordinate
    :type lat: float
    :param lon: Latitude of coordinate
    :type lon: float
    """
    lat: float
    lon: float


def geoid_to_coordinate(geoid: GeoId) -> Coordinate:
    """
    Convert a GeoId to a Coordinate

    :param geoid: geoid to convert
    :return: Coordinate
    """
    coord = h3.h3_to_geo(geoid)
    return Coordinate(coord[0], coord[1])


def coordinate_to_geoid(coordinate: Coordinate, resolution: int) -> GeoId:
    """
    Convert a Coordinate to a Geoid at a specific resolution

    :param coordinate: Coordinate to convert
    :param resolution: desired h3 resolution of the GeoId
    :rtype: :py:obj:`GeoId`
    :return: Geoid
    """
    geoid = h3.geo_to_h3(coordinate.lat, coordinate.lon, resolution)
    return geoid


def dist_euclidian(a: Coordinate, b: Coordinate) -> float:
    """
    Calculate the euclidian distance between two coordinates.

    .. warning::
        Calculating euclidian distance on latitude and longitude will introduce some error.

    :param a: Coordinate a
    :param b: Coordinate b
    :return: unitless distance between the two coordinates
    """
    return sqrt(pow((a.lat - b.lat), 2) + pow((a.lon - b.lon), 2))


def dist_haversine(a: Coordinate, b: Coordinate) -> Kilometers:
    """
    Calculate the haversine distance between two coordinates.

    :param a: Coordinate a
    :param b: Coordinate b
    :rtype: :py:obj:`km`
    :return: Distance between the two points in kilometers.
    """
    return haversine(a, b)


def interpolate_between_coordinates(a: Coordinate, b: Coordinate, ratio: Ratio) -> Coordinate:
    """
    Interpolate a new coordinate between two coordinates given a ratio using linear interpolation.

    .. warning::
        Using linear interpolation with latitude and longitude will introduce some error.

    :param a: Coordinate a
    :param b: Coordinate b
    :param ratio: ratio from a -> b
    :return: new interpolated Coordinate
    """
    # TODO: Right now this is just a linear interpolation. Do we want/need a more accurate interpolation?
    lat = a.lat + (b.lat - a.lat) * ratio
    lon = a.lon + (b.lon - a.lon) * ratio
    return Coordinate(lat, lon)
