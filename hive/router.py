import numpy as np
import requests

from hive import units
from hive.helpers import estimate_vmt_latlon


class OSRMRouteEngine:
    """
    Wrapper for OSRM routing engine.

    This engine expects that an OSRM server is running and that the address is given
    through the :code:`server` argument.

    Parameters
    ----------
    server: string
        The https address of the OSRM server.
    timestep_s: int
        The amount of seconds that each time step represents.
    """
    def __init__(self, server, timestep_s):
        self.server = server
        self.TIMESTEP_S = timestep_s
    def route(self, olat, olon, dlat, dlon, activity, trip_dist_mi=None, trip_time_s=None):
        addr = f'{self.server}/route/v1/driving/{olon},{olat};{dlon},{dlat}?overview=full&geometries=geojson&annotations=true'
        r = requests.get(addr)
        raw_json = r.json()
        raw_route = [(p[1], p[0]) for p in raw_json['routes'][0]['geometry']['coordinates']]
        durations = raw_json['routes'][0]['legs'][0]['annotation']['duration']
        dists = raw_json['routes'][0]['legs'][0]['annotation']['distance']
        route_time = np.cumsum(durations)
        route_dist = np.cumsum(dists) * units.METERS_TO_MILES
        bins = np.arange(0,max(route_time), self.TIMESTEP_S)
        route_index = np.digitize(route_time, bins)
        route = [(raw_route[0], route_dist[0], activity)]
        prev_index = 0
        for i in range(1, len(bins)+1):
            try:
                index = np.max(np.where(np.digitize(route_time, bins) == i))
            except ValueError:
                index = prev_index
            loc = raw_route[index]
            dist = route_dist[index] - route_dist[prev_index]
            route.append((loc, dist, activity))
            prev_index = index

        return route

class DefaultRouteEngine:
    """
    Default routing engine for hive.

    Using a calculated road network scaling factor and an average driving speed,
    the engine produces a scaled 'as the crow flies' path between the two points.

    Parameters
    ----------
    timestep_s: int
        The amount of seconds that each time step represents.
    rn_scaling_factor: float
        The calculated road network scaling factor
    dispatch_mph: float
        The calculated average driving speed
    """
    def __init__(self, timestep_s, rn_scaling_factor, dispatch_mph):
        self.TIMESTEP_S = timestep_s
        self.RN_SCALING_FACTOR = rn_scaling_factor
        self.DISPATCH_MPH = dispatch_mph
    def route(self, olat, olon, dlat, dlon, activity, trip_dist_mi=None, trip_time_s=None):
        if trip_dist_mi is None:
            trip_dist_mi = estimate_vmt_latlon(olat, olon, dlat, dlon, self.RN_SCALING_FACTOR)
        if trip_time_s is None:
            trip_time_s = (trip_dist_mi / self.DISPATCH_MPH) * units.HOURS_TO_SECONDS

        steps = round(trip_time_s/self.TIMESTEP_S)

        if steps <= 1:
            return [((olat, olon), trip_dist_mi, activity), ((dlat, dlon), trip_dist_mi, activity)]
        step_distance_mi = trip_dist_mi/steps
        route_range = np.arange(0, steps + 1)
        route = []
        for i, time in enumerate(route_range):
            t = i/steps
            xt = (1-t)*olat + t*dlat
            yt = (1-t)*olon + t*dlon
            point = (xt, yt)
            route.append((point, step_distance_mi, activity))
        return route
