"""
Helper functions for the HIVE platform
"""
import math
from haversine import haversine
import numpy as np

from hive.units import METERS_TO_MILES, KILOMETERS_TO_MILES

def haversine_np(lat1, lon1, lat2, lon2):
    """
    Function calculates the haversine distance between one or many points.

    Parameters
    ----------
    lat1: np.ndarray
        Array of latitudes
    lon1: np.ndarray
        Array of longitudes
    lat2: np.ndarray
        Array of latitudes
    lon2: np.ndarray
        Array of longitudes

    Returns
    -------
    distance_mi: np.ndarray
        Array of distances in miles.
    """
    lon1 = np.radians(lon1)
    lat1 = np.radians(lat1)
    lat2 = np.radians(lat2)
    lon2 = np.radians(lon2)

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = np.sin(dlat/2.0)**2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon/2.0)**2

    c = 2 * np.arcsin(np.sqrt(a))
    distance_mi = 6367 * c * KILOMETERS_TO_MILES
    return distance_mi

def estimate_vmt_latlon(olat, olon, dlat, dlon, scaling_factor):
    """
    Function calculates scaled haversine distance between two sets of latitude/
    longitude coordinates.

    Function calculates the shortest path distance between two sets of
    coordinates then scales this value by scaling_factor to more accurately
    approximate on-road vehicle miles traveled (VMT).

    Parameters
    ----------
    olat: double precision
        Latitude of origin
    olon: double precision
        Longitude of origin
    dlat: double precision
        Latitude of destination
    dlon: double precision
        Longitude of destination
    scaling_factor: double precision
        Scaling factor for estimating on-road VMT from shortest path distance

    Returns
    -------
    double precision
        Estimated VMT between two sets of coordinates
    """

    shortest_path_mi = haversine((olat, olon), (dlat, dlon), unit='mi')
    estimated_vmt_mi = shortest_path_mi * scaling_factor

    return estimated_vmt_mi

def estimate_vmt_2D(x1, y1, x2, y2, scaling_factor):
    """
    Function calculates euclidian distance between two sets of x,y coordinates.

    Function calculates the shortest path distance between two sets of
    coordinates then scales this value by scaling_factor to more accurately
    approximate on-road vehicle miles traveled (VMT).

    Parameters
    ----------
    x1: double precision
        x position of origin
    y1: double precision
        y position of origin
    x2: double precision
        x position of destination
    y2: double precision
        y position of destination
    scaling_factor: double precision
        Scaling factor for estimating on-road VMT from shortest path distance

    Returns
    -------
    double precision
        Estimated VMT between two sets of coordinates
    """

    shortest_path_mi = math.hypot(x2 - x1, y2 - y1) * METERS_TO_MILES
    estimated_vmt_mi = shortest_path_mi * scaling_factor

    return estimated_vmt_mi
