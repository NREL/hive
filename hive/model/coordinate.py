from typing import NamedTuple
from math import sqrt, pow


class Coordinate(NamedTuple):
    """
    a latitude (y) and longitude (x) tuple
    """
    lat: float
    lon: float


def dist_euclidian(a: Coordinate, b: Coordinate) -> float:
    return sqrt(pow((a.lat - b.lat), 2) + pow((a.lon - b.lon), 2))


