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
from hive.constraints import VEH_PARAMS
from hive.utils import assert_constraint, initialize_log, write_log
from hive.units import METERS_TO_MILES, HOURS_TO_SECONDS

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

    _FLEET_STATE_IDX = {
        'x': 0,
        'y': 1,
        'active': 2,
        'soc': 3,
    }

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
                environment_params,
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
        self.base = None
        self.avail_time = None
        self.avail_seats = max_passengers
        self.history = []

        assert_constraint('INITIAL_SOC', initial_soc, VEH_PARAMS, context="Initialize Vehicle")
        self._energy_kwh = battery_capacity * initial_soc

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

        self.ENV = environment_params
        # for param, val in environment_params.items():
        #     assert param in ENV_PARAMS.keys(), "Got an unexpected parameter {}.".format(param)
        #     assert_constraint(param, val, ENV_PARAMS, context="Initialize Vehicle")
        #     self.ENV[param] = val

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
        self._x = val
        self._set_fleet_state('x', val)

    @property
    def y(self):
        return self._y

    @y.setter
    def y(self, val):
        self._y = val
        self._set_fleet_state('y', val)

    @property
    def active(self):
        col = self._FLEET_STATE_IDX['active']
        return bool(self.fleet_state[self.ID, col])

    @active.setter
    def active(self, val):
        assert type(val) is bool, "This variable must be boolean"
        self._set_fleet_state('active', int(val))

    @property
    def soc(self):
        col = self._FLEET_STATE_IDX['soc']
        return self.fleet_state[self.ID, col]

    @soc.setter
    def soc(self, val):
        raise NotImplementedError('Please do not update soc directly. Use energy_kwh.')

    @property
    def energy_kwh(self):
        return self._energy_kwh

    @energy_kwh.setter
    def energy_kwh(self, val):
        soc = val / self.BATTERY_CAPACITY
        self._set_fleet_state('soc', soc)
        self._energy_kwh = val

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

    def _set_fleet_state(self, param, val):
        col = self._FLEET_STATE_IDX[param]
        self.fleet_state[self.ID, col] = val

    def _distance(self, x0, y0, x1, y1):
        return math.hypot(x1-x0, y1-y0) * METERS_TO_MILES * self.ENV['RN_SCALING_FACTOR']

    def _update_charge(self, dist_mi):
        spd = self.ENV['DISPATCH_MPH']
        lookup = self.WH_PER_MILE_LOOKUP
        kwh__mi = (np.interp(spd, lookup['avg_spd_mph'], lookup['whmi']))/1000.0
        energy_used_kwh = dist_mi * kwh__mi
        self.energy_kwh -= energy_used_kwh

    def _move(self):
        if self._route is not None:
            try:
                time, location = next(self._route_iter)
                new_x = location[0]
                new_y = location[1]
                assert(time == (self._clock.now+1))
                dist_mi = self._distance(self.x, self.y, new_x, new_y)
                self.x = new_x
                self.y = new_y
            except StopIteration:
                self._route = None
                self.active = True

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
        # print(f"Vehicle {self.ID} making trip from ({origin_x}, {origin_y}) to ({destination_x}, {destination_y})")

        if trip_dist_mi is None:
            trip_dist_mi = math.hypot(destination_x - origin_x, destination_y - origin_y)\
                * METERS_TO_MILES * self.ENV['RN_SCALING_FACTOR']
        if trip_time_s is None:
            trip_time_s = (trip_dist_mi / self.ENV['DISPATCH_MPH']) * HOURS_TO_SECONDS

        disp_dist_mi = math.hypot(origin_x - self.x, origin_y - self.y) \
                * METERS_TO_MILES * self.ENV['RN_SCALING_FACTOR']
        disp_time_s = (disp_dist_mi / self.ENV['DISPATCH_MPH']) * HOURS_TO_SECONDS
        disp_route = self._generate_route(self.x, self.y, origin_x, origin_y, disp_time_s, current_sim_time)

        trip_sim_time = disp_route[-1][0]
        trip_route = self._generate_route(origin_x, origin_y, destination_x, destination_y, trip_time_s, trip_sim_time)

        del disp_route[-1]
        self._route = disp_route + trip_route
        self._route_iter = iter(self._route)
        self.active = False
        next(self._route_iter)

    def cmd_travel_to(self,
                  destination_x,
                  destination_y,
                  trip_dist_mi=None,
                  trip_time_s=None):

        current_sim_time = self._clock.now

        if trip_dist_mi is None:
            trip_dist_mi = math.hypot(destination_x - self.x, destination_y - self.y) \
                    * METERS_TO_MILES * self.ENV['RN_SCALING_FACTOR']
        if trip_time_s is None:
            trip_time_s = (trip_dist_mi / self.ENV['DISPATCH_MPH']) * HOURS_TO_SECONDS

        self._route = self.generate_route(self.x, self.y, destination_x, destination_y, trip_time_s, current_sim_time)
        self._route_iter = iter(self._route)
        next(self._route_iter)

    def step(self):
        self._move()
        self.history.append((self.x, self.y))
