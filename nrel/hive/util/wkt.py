import functools as ft
from typing import Tuple


def polygon_empty() -> str:
    return "POLYGON EMPTY"


def _point_to_string(point: Tuple[float, float], x_y_ordering: bool) -> str:
    """
    converts a point tuple into a string pair for wkt printing

    :param point: a point in (Lat, Lon) ordering (y, x)
    :param x_y_ordering: if the output should be reversed into (x, y) ordering
    :return: a string pair for wkt printing
    """
    if x_y_ordering:
        return f"{point[1]} {point[0]}"
    else:
        return f"{point[0]} {point[1]}"


def point_2d(point: Tuple[float, float], x_y_ordering: bool) -> str:
    """
    creates a point when provided a pair, otherwise, returns an empty polygon

    :param point: a point in (Lat, Lon) ordering (y, x)
    :param x_y_ordering: if the output should be reversed into (x, y) ordering
    :return: a wkt point, tuple order preserved
    """
    if not isinstance(point, tuple) or len(point) != 2:
        return polygon_empty()
    else:
        point_str = f"POINT ({_point_to_string(point, x_y_ordering)})"
        return point_str


def linestring_2d(points: Tuple[Tuple[float, float], ...], x_y_ordering: bool) -> str:
    """
    creates a linestring from a sequence of points, or, returns an empty
    polygon if no points are provided

    :param points: a sequence of points in (Lat, Lon) ordering (y, x)
    :param x_y_ordering: if the output should be reversed into (x, y) ordering
    :return: a wkt representation
    """
    if not isinstance(points, tuple) or len(points) == 0:
        return polygon_empty()
    elif len(points) == 1:
        return point_2d(points[0], x_y_ordering)
    else:
        initial: Tuple[str, ...] = tuple()
        pts_strings = ft.reduce(
            lambda acc, pair: acc + (f"{_point_to_string(pair, x_y_ordering)}",),
            points,
            initial,
        )
        inner_content = ", ".join(pts_strings)
        linestring = f"LINESTRING ({inner_content})"
        return linestring
