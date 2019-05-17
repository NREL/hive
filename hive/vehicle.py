"""
Vehicle object for the HIVE algorithm
"""

import sys
import csv
import datetime
from haversine import haversine

from hive import tripenergy as nrg
from hive import charging as chrg
from hive.constraints import ENV_PARAMS, VEH_PARAMS
from hive.utils import assert_constraint


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
        False, vehicle is sitting at depot
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

    def __init__(
                self,
                veh_id,
                name,
                battery_capacity,
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

        self.avail_lat = None
        self.avail_lon = None
        self.avail_time = 0
        self.energy_remaining = battery_capacity * initial_soc
        self.soc = initial_soc
        self.active = False

        self._log = logfile

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

    def make_trip(self, req):

        # Unpack request
        pickup_time = req[3]
        dropoff_time = req[4]
        trip_dist = req[5]
        pickup_lat = req[6]
        pickup_lon = req[7]
        dropoff_lat = req[8]
        dropoff_lon = req[9]
        passengers = req[10]

        #TODO: refactor make_trip behavior


        with open(self._log,'a') as f:
            writer = csv.writer(f)

            if inpt.CHARGING_SCENARIO == 'Ubiq': #ubiquitous charging assumption
                # Update w/ idle
                idle_start = self.avail_time
                if diff_s <= (inpt.MINUTES_BEFORE_CHARGE * 60):
                    idle_s = diff_s
                    if report:
                        self.stats['idle_s'] += idle_s
                    self.energy_remaining -= nrg.calc_idle_kwh(idle_s)
                    self.soc = self.energy_remaining/self.BATTERY_CAPACITY

                    if idle_s > 0:
                        idle_end = idle_start + idle_s
                        dispatch_start = idle_end
                        writer.writerow([self.id, -1, idle_start, self.avail_lat, self.avail_lon, idle_end, self.avail_lat, self.avail_lon, 0, round(self.soc, 2), 0])
                else:
                    idle_s = inpt.MINUTES_BEFORE_CHARGE * 60
                    if report:
                        self.stats['idle_s'] += idle_s
                    self.energy_remaining -= nrg.calc_idle_kwh(idle_s)
                    self.soc = self.energy_remaining/self.BATTERY_CAPACITY
                    idle_end = idle_start + idle_s
                    refuel_start = idle_end
                    writer.writerow([self.id, -1, idle_start, self.avail_lat, self.avail_lon, idle_end, self.avail_lat, self.avail_lon, 0, round(self.soc, 2), 0])

                    # Update w/ charging
                    pwr = inpt.UBIQUITOUS_CHARGER_POWER
                    secs_to_full = chrg.calc_const_charge_secs_to_full(self.energy_remaining, self.BATTERY_CAPACITY, kw=pwr)
                    if secs_to_full >= (diff_s - idle_s):
                        refuel_s = diff_s - idle_s
                        if report:
                            self.stats['refuel_s'] += refuel_s
                        self.energy_remaining = self.energy_remaining + chrg.calc_const_charge_kwh(refuel_s, kw=pwr)
                        self.soc = self.energy_remaining/self.BATTERY_CAPACITY
                        refuel_end = refuel_start + refuel_s
                        dispatch_start = refuel_end
                        if report:
                            self.stats['refuel_cnt'] += 1
                        writer.writerow([self.id, -3, refuel_start, self.avail_lat, self.avail_lon, refuel_end, self.avail_lat, self.avail_lon, 0, round(self.soc, 2), 0])
                    else:
                        refuel_s = secs_to_full
                        if report:
                            self.stats['refuel_s'] += refuel_s
                        self.energy_remaining = self.BATTERY_CAPACITY
                        self.soc = self.energy_remaining/self.BATTERY_CAPACITY
                        if refuel_s > 0:
                            refuel_end = refuel_start + refuel_s
                            idle2_start = refuel_end
                            if report:
                                self.stats['refuel_cnt'] += 1
                            writer.writerow([self.id, -3, refuel_start, self.avail_lat, self.avail_lon, refuel_end, self.avail_lat, self.avail_lon, 0, round(self.soc, 2), 0])

                        # Update w/ second idle event after charge to full
                        idle2_s = diff_s - idle_s - refuel_s
                        if report:
                            self.stats['idle_s'] += idle2_s
                        self.energy_remaining -= nrg.calc_idle_kwh(idle2_s)
                        self.soc = self.energy_remaining/self.BATTERY_CAPACITY
                        idle2_end = idle2_start + idle2_s
                        dispatch_start = idle2_end
                        writer.writerow([self.id, -1, idle2_start, self.avail_lat, self.avail_lon, idle2_end, self.avail_lat, self.avail_lon, 0, round(self.soc, 2), 0])

            elif inpt.CHARGING_SCENARIO == 'Station': # NO ubiquitous charging assumption
                idle_start = self.avail_time
                idle_s = diff_s
                if report:
                    self.stats['idle_s'] += idle_s
                self.energy_remaining -= nrg.calc_idle_kwh(idle_s)
                self.soc = self.energy_remaining/self.BATTERY_CAPACITY
                if idle_s > 0:
                    idle_end = idle_start + idle_s
                    dispatch_start = idle_end
                    writer.writerow([self.id, -1, idle_start, self.avail_lat, self.avail_lon, idle_end, self.avail_lat, self.avail_lon, 0, round(self.soc, 2), 0])

            # Update w/ dispatch
            if report:
                self.stats['dispatch_vmt'] += dispatch_dist
                self.stats['total_vmt'] += dispatch_dist

            if dispatch_dist > 0:
                dispatch_time_s = otime - dispatch_start
                if report:
                    self.stats['dispatch_s'] += dispatch_time_s
                self.energy_remaining -= nrg.calc_trip_kwh(dispatch_dist, dispatch_time_s, self.WH_PER_MILE_LOOKUP)
                self.soc = self.energy_remaining/self.BATTERY_CAPACITY
                writer.writerow([self.id, -2, dispatch_start, self.avail_lat, self.avail_lon, otime, olat, olon, dispatch_dist, round(self.soc, 2), 0])

            # Update w/ trip
            self.avail_lat = dlat
            self.avail_lon = dlon
            self.avail_time = dtime
            if report:
                self.stats['trip_vmt'] += trip_dist
                self.stats['total_vmt'] += trip_dist
            trip_time_s = dtime - otime
            if report:
                self.stats['trip_s'] += trip_time_s

            if trip_time_s > 0:
                self.energy_remaining -= nrg.calc_trip_kwh(trip_dist, trip_time_s, self.WH_PER_MILE_LOOKUP)

            self.soc = self.energy_remaining / self.BATTERY_CAPACITY
            if report:
                self.stats['requests_filled'] += 1
                self.stats['passengers_delivered'] += passengers
            writer.writerow([self.id, trip_id, otime, olat, olon, dtime, dlat, dlon, trip_dist, round(self.soc, 2), passengers])


    def refuel(self, charg_stations, final_soc, report):

        #TODO: refactor refuel behavior

        with open(self._log, 'a') as f:
            writer = csv.writer(f)

            # Locate nearest station
            nearest_station = charg_stations[0]
            dist_to_nearest = haversine((self.avail_lat, self.avail_lon), (nearest_station.lat, nearest_station.lon), unit='mi') * inpt.self.ENV['RN_SCALING_FACTOR']
            for station in charg_stations[1:]:
                dist = haversine((self.avail_lat, self.avail_lon), (station.lat, station.lon), unit='mi') * inpt.self.ENV['RN_SCALING_FACTOR']
                if dist < dist_to_nearest:
                    nearest_station = station
                    dist_to_nearest = dist

            # Dispatch to station
            if report:
                self.stats['dispatch_vmt'] += dist_to_nearest
                self.stats['total_vmt'] += dist_to_nearest

            if dist_to_nearest > 0:
                dispatch_time_s = dist_to_nearest / inpt.self.ENV['DISPATCH_MPH'] * 3600
                if report:
                    self.stats['dispatch_s'] += dispatch_time_s
                dispatch_start = self.avail_time
                dispatch_end = dispatch_start + dispatch_time_s
                self.energy_remaining -= nrg.calc_trip_kwh(dist_to_nearest, dispatch_time_s, self.WH_PER_MILE_LOOKUP)
                self.soc = max(0, self.energy_remaining/self.BATTERY_CAPACITY)
                writer.writerow([self.id, -2, dispatch_start, self.avail_lat, self.avail_lon, dispatch_end, nearest_station.lat, nearest_station.lon, dist_to_nearest, round(self.soc, 2), 0])

            # Charge at station
            self.avail_lat = nearest_station.lat
            self.avail_lon = nearest_station.lon
            soc_i = self.soc
            charge_time = chrg.query_charge_stats(self.CHARGE_TEMPLATE, soc_i=soc_i*100, soc_f=final_soc*100)[2]
            if report:
                self.stats['refuel_s'] += charge_time
            start_time = dispatch_end
            end_time = dispatch_end + charge_time
            self.avail_time = end_time
            self.soc = final_soc
            self.energy_remaining = self.soc * self.BATTERY_CAPACITY
            if report:
                self.stats['refuel_cnt'] += 1
            writer.writerow([self.id, -3, start_time, self.avail_lat, self.avail_lon,
                             end_time, self.avail_lat, self.avail_lon, 0, self.soc, 0])
            nearest_station.add_recharge(self.id, start_time, end_time, soc_i, final_soc)


    def return_to_depot(self, depot):
        with open(self._log,'a') as f:
            writer = csv.writer(f)

            dispatch_dist = haversine((self.avail_lat, self.avail_lon), (depot.LAT, depot.LON), unit='mi') * self.ENV['RN_SCALING_FACTOR']
            self.stats['dispatch_vmt'] += dispatch_dist
            self.stats['total_vmt'] += dispatch_dist
            dispatch_time_s = dispatch_dist / self.ENV['DISPATCH_MPH'] * 3600
            self.stats['dispatch_s'] += dispatch_time_s
            self.energy_remaining -= nrg.calc_trip_kwh(dispatch_dist, dispatch_time_s, self.WH_PER_MILE_LOOKUP)
            self.soc = self.energy_remaining/self.BATTERY_CAPACITY
            dtime = self.avail_time + datetime.timedelta(seconds=dispatch_time_s)

            # Update log w/ dispatch to depot
            writer.writerow([self.id, #veh id
                            -2, #activitycode
                            self.avail_time, #otime
                            self.avail_lat, #olat
                            self.avail_lon, #olon
                            dtime, #dtime
                            depot.LAT, #dlat
                            depot.LON, #dlon
                            dispatch_dist, #miles traveled
                            round(self.soc, 2), #dsoc
                            0]) #passengers

            # Update vehicle state
            self.active = False
            self.avail_lat, self.avail_lon = depot.LAT, depot.LON
            self.avail_time = dtime
