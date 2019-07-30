"""
Vehicle object for the HIVE platform
"""

import sys
import csv
import datetime
import numpy as np
import utm
import math

from hive import helpers as hlp
from hive import tripenergy as nrg
from hive import charging as chrg
from hive.constraints import ENV_PARAMS, VEH_PARAMS
from hive.utils import assert_constraint, initialize_log, write_log

sys.path.append('..')
from config import SIMULATION_PERIOD_SECONDS


class Vehicle:
    """
    Base class for vehicle in ride sharing fleet.

    Inputs
    ------
    veh_id : int
        Identifer assigned to vehicle object
    battery_capacity : double precision
        Battery capacity in kWh
    initial_soc: double precision
        Initial SOC in range [0,1]
    whmi_lookup: pd.DataFrame
        Wh/mile lookup DataFrame
    charge_template: pd.DataFrame
        Charge template DataFrame
    logfile: str
        Path to vehicle log file

    Attributes
     ----------
    energy_remaining: double precision
        Approx. energy remaining in battery (in kWh)
    soc: double precision
        Current battery state of charge
    avail_seats: int
        Current number of seats available
    trip_vmt: double precision
        Miles traveled serving ride requests
    dispatch_vmt: double precision
        Miles traveled dispatching to pickup locations
    total_vmt: double precision
        Total miles traveled
    requests_filled: int
        Total requests filled
    passengers_delivered: int
        Total passengers delivered
    refuel_cnt: int
        Number of refuel events
    idle_s: double precision
        Seconds where a vehicle is not serving a request or dispatching to request
    active: boolean
        Boolean indicator for whether a veh is actively servicing demand. If
        False, vehicle is sitting at a base
    _base: dict
        Lookup for base charging information.
    """
    # statistics tracked on a vehicle instance level over entire simulation.
    _STATS = [
            'veh_id',
            'request_vmt',
            'dispatch_vmt',
            'total_vmt',
            'requests_filled',
            'passengers_delivered',
            'base_refuel_cnt',
            'station_refuel_cnt',
            'base_refuel_s',
            'station_refuel_s',
            'refuel_energy_kwh',
            'idle_s',
            'dispatch_s',
            'base_reserve_s',
            'request_s',
            'end_soc',
            'pct_time_trip',
            ]

    _LOG_COLUMNS = [
                'veh_id',
                'activity',
                'start_time',
                'start_lat',
                'start_lon',
                'end_time',
                'end_lat',
                'end_lon',
                'dist_mi',
                'start_soc',
                'end_soc',
                'passengers'
                ]

    def __init__(
                self,
                veh_id,
                name,
                battery_capacity,
                max_charge_acceptance,
                max_passengers,
                initial_soc,
                whmi_lookup,
                charge_template,
                logfile,
                clock,
                environment_params = dict(),
                ):

        # Public Constants
        self.ID = veh_id
        self.NAME = name
        assert_constraint('BATTERY_CAPACITY', battery_capacity, VEH_PARAMS, context="Initialize Vehicle")
        self.BATTERY_CAPACITY = battery_capacity
        self.MAX_CHARGE_ACCEPTANCE_KW = max_charge_acceptance
        self.WH_PER_MILE_LOOKUP = whmi_lookup
        self.CHARGE_TEMPLATE = charge_template

        # Public variables
        self.active = False
        self.base = None
        self.avail_time = None
        self.avail_seats = max_passengers
        assert_constraint('INITIAL_SOC', initial_soc, VEH_PARAMS, context="Initialize Vehicle")
        self.soc = initial_soc
        self.energy_remaining = battery_capacity * initial_soc
        self.history = []

        self._logfile = logfile

        # Postition variables
        self._x = None
        self._y = None

        self._route = None
        self._route_iter = None

        self._clock = clock

        self.fleet_state = None

        # Init reporting
        self.stats = dict()
        for stat in self._STATS:
            self.stats[stat] = 0
        self.stats['veh_id'] = veh_id

        self.ENV = dict()
        for param, val in environment_params.items():
            assert param in ENV_PARAMS.keys(), "Got an unexpected parameter {}.".format(param)
            assert_constraint(param, val, ENV_PARAMS, context="Initialize Vehicle")
            self.ENV[param] = val

    @property
    def latlon(self):
        return utm.to_latlon(self._x, self._y, self._zone_number, self._zone_letter)

    @latlon.setter
    def latlon(self, val):
        try:
            lat, lon = val
        except ValueError:
            raise ValueError('Pass iterable with lat lon pair')
        else:
            x, y, zone_number, zone_letter = utm.from_latlon(lat, lon)
            self._x = x
            self._y = y
            self._zone_number = zone_number
            self._zone_letter = zone_letter

    @property
    def x(self):
        return self._x

    @x.setter
    def x(self, val):
        #TODO: Add fleet state matrix
        self._x = val

    @property
    def y(self):
        return self._y

    @y.setter
    def y(self, val):
        #TODO: Add fleet state matrix
        self._y = val

    def __repr__(self):
        return str(f"Vehicle(id: {self.ID}, name: {self.NAME})")


    def dump_stats(self, filepath):
        self.stats['end_soc'] = self.soc

        try:
            self.stats['pct_time_trip'] = self.stats['request_s'] / (self.stats['station_refuel_s'] \
                + self.stats['idle_s'] + self.stats['dispatch_s'] + self.stats['request_s'] + self.stats['base_refuel_s'])
        except ZeroDivisionError:
            self.stats['pct_time_trip'] = 0

        write_log(self.stats, self._STATS, filepath)

    def _update_location(self):
        if self._route is not None:
            try:
                time, location = next(self._route_iter)
                assert(time == (self._clock.now+1))
                self.x = location[0]
                self.y = location[1]
            except StopIteration:
                self._route = None

    def _generate_route(self, x0, y0, x1, y1, trip_time_s, sim_time):
        steps = round(trip_time_s/SIMULATION_PERIOD_SECONDS)
        if steps <= 1:
            return [(sim_time, (x0, y0)), (sim_time+1, (x1, y1))]
        route_range = np.arange(sim_time, sim_time + steps + 1)
        route = []
        for i, time in enumerate(route_range):
            t = i/steps
            xt = (1-t)*x0 + t*x1
            yt = (1-t)*y0 + t*y1
            point = (xt, yt)
            route.append((int(time), point))
        return route

    def cmd_make_trip(self,
                 origin_x,
                 origin_y,
                 destination_x,
                 destination_y,
                 trip_dist_mi=None,
                 trip_time_s=None):

        current_sim_time = self._clock.now

        if trip_dist_mi is None:
            trip_dist_mi = math.hypot(destination_x - origin_x, destination_y - origin_y) * METERS_TO_MILES * RN_SCALING_FACTOR
        if trip_time_s is None:
            trip_time_s = (trip_dist_mi / VEH_AVG_MPH) * HOURS_TO_SECONDS

        disp_dist_mi = math.hypot(origin_x - self.x, origin_y - self.y) * METERS_TO_MILES * RN_SCALING_FACTOR
        disp_time_s = (disp_dist_mi / VEH_AVG_MPH) * HOURS_TO_SECONDS
        disp_route = self._generate_route(self.x, self.y, origin_x, origin_y, disp_time_s, current_sim_time)

        trip_sim_time = disp_route[-1][0]
        trip_route = self._generate_route(origin_x, origin_y, destination_x, destination_y, trip_time_s, trip_sim_time)

        del disp_route[-1]
        self._route = disp_route + trip_route
        self._route_iter = iter(self.route)
        next(self._route_iter)

    def cmd_travel_to(self,
                  destination_x,
                  destination_y,
                  trip_dist_mi=None,
                  trip_time_s=None):

        current_sim_time = self._clock.now

        if trip_dist_mi is None:
            trip_dist_mi = math.hypot(destination_x - self.x, destination_y - self.y) * METERS_TO_MILES * RN_SCALING_FACTOR
        if trip_time_s is None:
            trip_time_s = (trip_dist_mi / VEH_AVG_MPH) * HOURS_TO_SECONDS

        self._route = self.generate_route(self.x, self.y, destination_x, destination_y, trip_time_s, current_sim_time)
        self._route_iter = iter(self.route)
        next(self._route_iter)

    def step(self):
        self._update_location()
        self.history.append((self.x, self.y))
