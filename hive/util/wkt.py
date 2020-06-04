from typing import Tuple

import functools as ft


def polygon_empty() -> str:
    return "POLYGON EMPTY"


def point_2d(point: Tuple[float, float]) -> str:
    """
    creates a point when provided a pair, otherwise, returns an empty polygon
    :param point: a point
    :return: a wkt point, tuple order preserved
    """
    if not isinstance(point, Tuple) or len(point) != 2:
        return polygon_empty()
    else:
        point_str = f"POINT ({point[0]} {point[1]})"
        return point_str


def linestring_2d(points: Tuple[Tuple[float, float], ...]) -> str:
    """
    creates a linestring from a sequence of points, or, returns an empty
    polygon if no points are provided
    :param points: a sequence of points in lat/lon format
    :return: a wkt representation
    """
    if not isinstance(points, Tuple) or len(points) == 0:
        return polygon_empty()
    elif len(points) == 1:
        return point_2d(points[0])
    else:
        pts_strings = ft.reduce(lambda acc, pair: acc + (f"{pair[0]} {pair[1]}",), points, ())
        inner_content = ", ".join(pts_strings)
        linestring = f"LINESTRING ({inner_content})"
        return linestring
