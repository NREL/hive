"""
Vehicle object for the HIVE platform
"""

import sys
import csv
import datetime

from hive import helpers as hlp
from hive import tripenergy as nrg
from hive import charging as chrg
from hive.constraints import ENV_PARAMS, VEH_PARAMS
from hive.utils import assert_constraint, initialize_log, write_log


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
    energy_remaining:
        Approx. energy remaining in battery (in kWh)
    soc:
        Current battery state of charge
    avail_seats:
        Current number of seats available
    trip_vmt:
        Miles traveled serving ride requests
    dispatch_vmt:
        Miles traveled dispatching to pickup locations
    total_vmt:
        Total miles traveled
    requests_filled:
        Total requests filled
    passengers_delivered:
        Total passengers delivered
    refuel_cnt:
        Number of refuel events
    idle_s:
        Seconds where a vehicle is not serving a request or dispatching to request
    active:
        Boolean indicator for whether a veh is actively servicing demand. If
        False, vehicle is sitting at a base
    base:
        base_id of vehicle's home location or base assignment. Used 
    """
    # statistics tracked on a vehicle instance level over entire simulation.
    _STATS = [
            'trip_vmt', #miles traveled servicing ride requests
            'dispatch_vmt', #miles traveled dispatching to pickup locations
            'total_vmt', #total miles traveled
            'requests_filled',
            'passengers_delivered',
            'refuel_cnt', #number of refuel/recharge events
            'refuel_s', #seconds where a vehicle is charging
            'idle_s', #seconds where vehicle is not serving, dispatching to new request, or charging
            'dispatch_s', #seconds where vehicle is moving w/o passengers
            'trip_s', #seconds where vehicle is serving a trip request
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
                'end_soc',
                'passengers'
                ]

    def __init__(
                self,
                veh_id,
                name,
                battery_capacity,
                max_passengers,
                initial_soc,
                whmi_lookup,
                charge_template,
                logfile,
                environment_params = dict(),
                ):

        # Public Constants
        self.ID = veh_id
        self.NAME = name
        assert_constraint('BATTERY_CAPACITY', battery_capacity, VEH_PARAMS, context="Initialize Vehicle")
        self.BATTERY_CAPACITY = battery_capacity
        self.WH_PER_MILE_LOOKUP = whmi_lookup
        self.CHARGE_TEMPLATE = charge_template

        # Public variables
        self.active = False
        self.avail_lat = None
        self.avail_lon = None
        self.base = None
        self.avail_time = 0
        self.avail_seats = max_passengers
        assert_constraint('INITIAL_SOC', initial_soc, VEH_PARAMS, context="Initialize Vehicle")
        self.soc = initial_soc
        self.energy_remaining = battery_capacity * initial_soc

        # Init logging
        self._logfile = logfile
        initialize_log(self._LOG_COLUMNS, self._logfile)
        
        # Init reporting
        self.stats = dict()
        for stat in self._STATS:
            self.stats[stat] = 0

        self.ENV = dict()
        for param, val in environment_params.items():
            assert param in ENV_PARAMS.keys(), "Got an unexpected parameter {}.".format(param)
            assert_constraint(param, val, ENV_PARAMS, context="Initialize Vehicle")
            self.ENV[param] = val

    def __repr__(self):
        return str(f"Vehicle(id: {self.id}, name: {self.NAME})")

    def make_trip(self, request, calcs):
        pass

    #     # Unpack request
    #     pickup_time = req[3]
    #     dropoff_time = req[4]
    #     trip_dist = req[5]
    #     pickup_lat = req[6]
    #     pickup_lon = req[7]
    #     dropoff_lat = req[8]
    #     dropoff_lon = req[9]
    #     passengers = req[10]

    #     #TODO: refactor make_trip behavior

    #     idle_start = self.avail_time
    #     idle_s = request['']



    #     elif inpt.CHARGING_SCENARIO == 'Station': # NO ubiquitous charging assumption
    #         idle_start = self.avail_time
    #         idle_s = diff_s
    #         if report:
    #             self.stats['idle_s'] += idle_s
    #         self.energy_remaining -= nrg.calc_idle_kwh(idle_s)
    #         self.soc = self.energy_remaining/self.BATTERY_CAPACITY
    #         if idle_s > 0:
    #             idle_end = idle_start + idle_s
    #             dispatch_start = idle_end
    #             write_log([self.id, -1, idle_start, self.avail_lat, self.avail_lon, idle_end, self.avail_lat, self.avail_lon, 0, round(self.soc, 2), 0], self._logfile)

    #     # Update w/ dispatch
    #     if report:
    #         self.stats['dispatch_vmt'] += dispatch_dist
    #         self.stats['total_vmt'] += dispatch_dist

    #     if dispatch_dist > 0:
    #         dispatch_time_s = otime - dispatch_start
    #         if report:
    #             self.stats['dispatch_s'] += dispatch_time_s
    #         self.energy_remaining -= nrg.calc_trip_kwh(dispatch_dist, dispatch_time_s, self.WH_PER_MILE_LOOKUP)
    #         self.soc = self.energy_remaining/self.BATTERY_CAPACITY
    #         write_log([self.id, -2, dispatch_start, self.avail_lat, self.avail_lon, otime, olat, olon, dispatch_dist, round(self.soc, 2), 0], self._logfile)

    #     # Update w/ trip
    #     self.avail_lat = dlat
    #     self.avail_lon = dlon
    #     self.avail_time = dtime
    #     if report:
    #         self.stats['trip_vmt'] += trip_dist
    #         self.stats['total_vmt'] += trip_dist
    #     trip_time_s = dtime - otime
    #     if report:
    #         self.stats['trip_s'] += trip_time_s

    #     if trip_time_s > 0:
    #         self.energy_remaining -= nrg.calc_trip_kwh(trip_dist, trip_time_s, self.WH_PER_MILE_LOOKUP)

    #     self.soc = self.energy_remaining / self.BATTERY_CAPACITY
    #     if report:
    #         self.stats['requests_filled'] += 1
    #         self.stats['passengers_delivered'] += passengers
    #     write_log([self.id, trip_id, otime, olat, olon, dtime, dlat, dlon, trip_dist, round(self.soc, 2), passengers], self._logfile)


    # def refuel(self, charg_stations, final_soc, report):

    #     #TODO: refactor refuel behavior

    #     # Locate nearest station
    #     nearest_station = charg_stations[0]
    #     dist_to_nearest = 
        
    #     haversine((self.avail_lat, self.avail_lon), (nearest_station.lat, nearest_station.lon), unit='mi') * inpt.self.ENV['RN_SCALING_FACTOR']
    #     for station in charg_stations[1:]:
    #         dist = haversine((self.avail_lat, self.avail_lon), (station.lat, station.lon), unit='mi') * inpt.self.ENV['RN_SCALING_FACTOR']
    #         if dist < dist_to_nearest:
    #             nearest_station = station
    #             dist_to_nearest = dist

    #     # Dispatch to station
    #     if report:
    #         self.stats['dispatch_vmt'] += dist_to_nearest
    #         self.stats['total_vmt'] += dist_to_nearest

    #     if dist_to_nearest > 0:
    #         dispatch_time_s = dist_to_nearest / inpt.self.ENV['DISPATCH_MPH'] * 3600
    #         if report:
    #             self.stats['dispatch_s'] += dispatch_time_s
    #         dispatch_start = self.avail_time
    #         dispatch_end = dispatch_start + dispatch_time_s
    #         self.energy_remaining -= nrg.calc_trip_kwh(dist_to_nearest, dispatch_time_s, self.WH_PER_MILE_LOOKUP)
    #         self.soc = max(0, self.energy_remaining/self.BATTERY_CAPACITY)
    #         write_log([self.id, -2, dispatch_start, self.avail_lat, self.avail_lon, dispatch_end, nearest_station.lat, nearest_station.lon, dist_to_nearest, round(self.soc, 2), 0], self._logfile)

    #     # Charge at station
    #     self.avail_lat = nearest_station.lat
    #     self.avail_lon = nearest_station.lon
    #     soc_i = self.soc
    #     charge_time = chrg.query_charge_stats(self.CHARGE_TEMPLATE, soc_i=soc_i*100, soc_f=final_soc*100)[2]
    #     if report:
    #         self.stats['refuel_s'] += charge_time
    #     start_time = dispatch_end
    #     end_time = dispatch_end + charge_time
    #     self.avail_time = end_time
    #     self.soc = final_soc
    #     self.energy_remaining = self.soc * self.BATTERY_CAPACITY
    #     if report:
    #         self.stats['refuel_cnt'] += 1
    #     write_log([self.id, -3, start_time, self.avail_lat, self.avail_lon,
    #                      end_time, self.avail_lat, self.avail_lon, 0, self.soc, 0], self._logfile)
    #     nearest_station.add_recharge(self.id, start_time, end_time, soc_i, final_soc)


    # def return_to_base(self, base):
    #     """
    #     Function to send Vehicle to VehicleBase.

    #     Sends Vehicle to VehicleBase base and updates vehicle reporting
    #     attributes with an idle event and the dispatch event. As a result, 
    #     Vehicle "active" flag is flipped to False.

    #     Parameters
    #     ----------
    #     base: hive.stations.VehicleBase
    #         hive VehicleBase object assigned to Vehicle

    #     Returns
    #     -------
    #     None
    #     """

    #     # 1. Add idle event
    #     idle_time_s = self.ENV['MAX_ALLOWABLE_IDLE_MINUTES'] * 60
    #     idle_end = self.avail_time + datetime.timedelta(seconds=idle_time_s)
    #     self.energy_remaining -= nrg.calc_idle_kwh(idle_time_s)
    #     self.soc = self.energy_remaining / self.BATTERY_CAPACITY
    #     write_log({
    #         'veh_id': self.id,
    #         'activity': 'idle'
    #         'start_time': self.avail_time,
    #         'start_lat': self.avail_lat,
    #         'start_lon': self.avail_lon,
    #         'end_time': idle_end,
    #         'end_lat': self.avail_lat,
    #         'end_lon': self.avail_lon,
    #         'dist_mi': 0.0,
    #         'end_soc': round(self.soc, 2),
    #         'passengers': 0
    #     },
    #     self._LOG_COLUMNS,
    #     self._logfile)

    #     self.stats['idle_s'] += idle_time_s

    #     # 2. Add dispatch to base
    #     dispatch_dist_mi = haversine((self.avail_lat, self.avail_lon),
    #                             (base.LAT, base.LON), unit='mi') \
    #                                 * self.ENV['RN_SCALING_FACTOR']
    #     dispatch_time_s = dispatch_dist_mi / self.ENV['DISPATCH_MPH'] * 3600
    #     self.energy_remaining -= nrg.calc_trip_kwh(dispatch_dist_mi,
    #                                                 dispatch_time_s,
    #                                                 self.WH_PER_MILE_LOOKUP)
    #     self.soc = self.energy_remaining/self.BATTERY_CAPACITY
    #     dispatch_end = idle_end + datetime.timedelta(seconds=dispatch_time_s)

    #     # Update log w/ dispatch to base
    #     write_log({
    #         'veh_id': self.id,
    #         'activity': 'dispatch-base',
    #         'start_time': idle_end,
    #         'start_lat': self.avail_lat,
    #         'start_lon': self.avail_lon,
    #         'end_time': dispatch_end,
    #         'end_lat': base.LAT,
    #         'end_lon': base.LON,
    #         'dist_mi': dispatch_dist_mi,
    #         'end_soc': round(self.soc, 2),
    #         'passengers': 0
    #         },
    #         self._LOG_COLUMNS,
    #         self._logfile)


    #     self.stats['dispatch_s'] += dispatch_time_s
    #     self.stats['dispatch_vmt'] += dispatch_dist_mi
    #     self.stats['total_vmt'] += dispatch_dist_mi

    #     # Update Vehicle object
    #     self.active = False
    #     self.base = base.base_id
    #     self.avail_lat, self.avail_lon = base.LAT, base.LON
    #     self.avail_time = dispatch_end
