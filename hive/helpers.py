"""
Helper functions for the HIVE platform
"""

from haversine import haversine

def estimate_vmt(olat, olon, dlat, dlon, scaling_factor):
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
