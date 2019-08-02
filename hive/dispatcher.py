"""
Dispatcher Object for high-level decision making in HIVE. Includes functions for
vehicle dispatching, and DCFC station/base selection.
"""

import datetime
import sys
import numpy as np

from hive import tripenergy as nrg
from hive import charging as chrg
from hive import helpers as hlp
from hive.utils import write_log
from hive.units import METERS_TO_MILES

sys.path.append('..')
import config as cfg

class Dispatcher:
    """
    Base class for dispatcher.

    Inputs
    ------
    requests : list
        List of requests for simulation timestep

    Outputs
    -------

    """
    _STATS = [
        'failure_active_max_dispatch',
        'failure_active_time',
        'failure_active_battery',
        'failure_active_occupancy',
        'failure_inactive_time',
        'failure_inactive_battery',
        'failure_inactive_occupancy'
    ]

    _LOG_COLUMNS = [
        'pickup_time',
        'dropoff_time',
        'distance_miles',
        'pickup_lat',
        'pickup_lon',
        'dropoff_lat',
        'dropoff_lon',
        'passengers',
        'failure_active_max_dispatch',
        'failure_active_time',
        'failure_active_battery',
        'failure_active_occupancy',
        'failure_inactive_time',
        'failure_inactive_battery',
        'failure_inactive_occupancy'
        ]

    def __init__(
                self,
                fleet,
                fleet_state,
                stations,
                bases,
                clock,
                failed_requests_log
                ):

        self._fleet = fleet
        self._fleet_state = fleet_state
        for veh in self._fleet:
            veh.fleet_state = fleet_state

        self._clock = clock

        self._stations = stations
        self._bases = bases
        self._logfile = failed_requests_log

        self.stats = {}
        for stat in self._STATS:
            self.stats[stat] = 0

    def _reset_failure_tracking(self):
        """
        Resets internal failure type tracking log.
        """
        for stat in self._STATS:
            self.stats[stat] = 0

    def _get_n_closest_vehicles(self, fleet_state, request, n):
        mask = fleet_state[:,2] == 1
        point = np.array([(request.pickup_x, request.pickup_y)])
        dist = np.linalg.norm(fleet_state[:, :2] - point, axis=1) * METERS_TO_MILES
        best_vehs_idx = np.argsort(dist)
        return best_vehs_idx[mask[best_vehs_idx]][:n]

    def process_requests(self, requests):
        """
        process_requests is called for each simulation time step.

        Inputs
        ------
        requests - one or many requests to distribute to the fleet.
        """

        for request in requests.itertuples():
            best_vehicle = self._get_n_closest_vehicles(self._fleet_state, request, 1)
            if len(best_vehicle) < 1:
                # print("Dropped request at time {}".format(request.pickup_time))
                continue
            else:
                vehid = best_vehicle[0]
                veh = self._fleet[vehid]
                veh.cmd_make_trip(
                        request.pickup_x,
                        request.pickup_y,
                        request.dropoff_x,
                        request.dropoff_y,
                        trip_dist_mi=request.distance_miles,
                        trip_time_s=request.seconds)
