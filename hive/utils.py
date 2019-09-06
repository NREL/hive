import pandas as pd
import numpy as np
import requests
import sys
import glob
import os
import pickle
import csv
import shutil
import utm

from hive import units
from hive.helpers import estimate_vmt_2D

class Clock:
    """
    Iterator to store simulation time information.

    Parameters
    ----------
    timestep_s: int
        amount of seconds that one simulation time step represents.
    """
    def __init__(self, timestep_s):
        self.now = 0
        self.TIMESTEP_S = timestep_s
    def __next__(self):
        self.now += 1

class OSRMRouteEngine:
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
    def __init__(self, timestep_s, rn_scaling_factor, dispatch_mph):
        self.TIMESTEP_S = timestep_s
        self.RN_SCALING_FACTOR = rn_scaling_factor
        self.DISPATCH_MPH = dispatch_mph
    def route(self, olat, olon, dlat, dlon, activity, trip_dist_mi=None, trip_time_s=None):
        x0, y0, zone_number, zone_letter = utm.from_latlon(olat, olon)
        x1, y1, _, _ = utm.from_latlon(dlat, dlon)
        if trip_dist_mi is None:
            trip_dist_mi = estimate_vmt_2D(x0, y0, x1, y1, self.RN_SCALING_FACTOR)
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
            xt = (1-t)*x0 + t*x1
            yt = (1-t)*y0 + t*y1
            point = utm.to_latlon(xt, yt, zone_number, zone_letter)
            route.append((point, step_distance_mi, activity))
        return route


def save_to_hdf(data, outfile):
    """
    Function to save data to hdf5.
    """
    for key, val in data.items():
        val.to_hdf(outfile, key=key)

def save_to_pickle(data, outfile):
    """
    Function to save data to pickle.
    """
    with open(outfile, 'wb') as f:
        pickle.dump(data, f)


def build_output_dir(scenario_name, root_path):
    """
    Function to build scenario level output directory in root output directory.
    """
    scenario_output = os.path.join(root_path, scenario_name)
    if os.path.isdir(scenario_output):
        shutil.rmtree(scenario_output)
    os.makedirs(scenario_output)
    file_paths = {}
    log_path = os.path.join(scenario_output, 'logs')
    file_paths['log_path'] = log_path
    file_paths['summary_path'] = os.path.join(scenario_output, 'summaries')
    file_paths['vehicle_path'] = os.path.join(log_path, 'vehicles')
    file_paths['station_path'] = os.path.join(log_path, 'stations')
    file_paths['base_path'] = os.path.join(log_path, 'bases')
    file_paths['dispatcher_path'] = os.path.join(log_path, 'dispatcher')
    os.makedirs(file_paths['log_path'])
    os.makedirs(file_paths['vehicle_path'])
    os.makedirs(file_paths['station_path'])
    os.makedirs(file_paths['base_path'])
    os.makedirs(file_paths['dispatcher_path'])
    os.makedirs(file_paths['summary_path'])

    return file_paths

def assert_constraint(param, val, CONSTRAINTS, context=""):
    """
    Helper function to assert constraints at runtime.

    Parameters
    ----------
    param: str
        parameter of interest to check against constraint.
    val: int, float, str
        value of parameter that needs checking.
    CONSTRAINTS: dict
        dictionary of the constraints from hive.constraints.
    context: str
        context to inform the function what time of checking to perform.

    Notes
    -----

    Valid values for context:

    * between:        Check that value is between upper and lower bounds exclusive
    * between_incl:   Check that value is between upper and lower bounds inclusive
    * greater_than:   Check that value is greater than lower bound exclusive
    * less_than:      Check that value is less than upper bound exclusive
    * in_set:         Check that value is in a set
    """
    condition = CONSTRAINTS[param][0]

    if condition == 'between':
        assert val > CONSTRAINTS[param][1], \
            "Context: {} | Param {}:{} is under low limit {}"\
            .format(context, param, val, CONSTRAINTS[param][1])
        assert val < CONSTRAINTS[param][2], \
            "Context: {} | Param {}:{} is over high limit {}"\
            .format(context, param, val, CONSTRAINTS[param][2])
    elif condition == 'between_incl':
        assert val >= CONSTRAINTS[param][1], \
            "Context: {} | Param {}:{} is under low limit {}"\
            .format(context, param, val, CONSTRAINTS[param][1])
        assert val <= CONSTRAINTS[param][2], \
            "Context: {} | Param {}:{} is over high limit {}"\
            .format(context, param, val, CONSTRAINTS[param][2])
    elif condition == 'greater_than':
        assert val > CONSTRAINTS[param][1], \
            "Context: {} | Param {}:{} is under low limit {}"\
            .format(context, param, val, CONSTRAINTS[param][1])
    elif condition == 'less_than':
        assert val < CONSTRAINTS[param][1], \
            "Context: {} | Param {}:{} is over high limit {}"\
            .format(context, param, val, CONSTRAINTS[param][1])
    elif condition == 'in_set':
        assert val in CONSTRAINTS[param][1], \
            "Context: {} | Param {}:{} must be from set {}"\
            .format(context, param, val, CONSTRAINTS[param][1])
