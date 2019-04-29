"""
Vehicle object for the hive algorithm
"""

import sys
import csv
from haversine import haversine

from hive import tripenergy as nrg
from hive import charging as chrg
from hive.constraints import ENV_PARAMS


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
    """
    # statistics tracked on a vehicle instance level over entire simulation.
    STATS = [
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

        self.veh_id = veh_id
        self.name = name
        self.battery_capacity = battery_capacity
        self.avail_lat = 0
        self.avail_lon = 0
        self.avail_time = 0
        self.energy_remaining = battery_capacity * initial_soc
        self.soc = initial_soc

        self._wh_per_mile_lookup = whmi_lookup
        self._charge_template = charge_template
        self._log = logfile

        self._stats = dict()
        for stat in self.STATS:
            self._stats[stat] = 0

        self._ENV = dict()
        for param, val in environment_params.items():
            assert param in ENV_PARAMS.keys(), "Got an unexpected parameter {}.".format(param)
            assert val > ENV_PARAMS[param][0], "Param {}:{} is out of bounds {}".format(param, val, ENV_PARAMS[param])
            assert val < ENV_PARAMS[param][1], "Param {}:{} is out of bounds {}".format(param, val, ENV_PARAMS[param])
            self._ENV[param] = val

    def __repr__(self):
        return str(f"Vehicle(id: {self.veh_id}, name: {self.name})")


    #IDEA: I think we could let this function take the request as an input and then
    # just unpack the request properties internally. -NR
    def make_trip(
                self,
                trip_id,
                olat,
                olon,
                otime,
                dlat,
                dlon,
                dtime,
                trip_dist,
                dispatch_dist,
                diff_s,
                passengers,
                report
                ):
        with open(self._log,'a') as f:
            writer = csv.writer(f)

            if inpt.CHARGING_SCENARIO == 'Ubiq': #ubiquitous charging assumption
                # Update w/ idle
                idle_start = self.avail_time
                if diff_s <= (inpt.MINUTES_BEFORE_CHARGE * 60):
                    idle_s = diff_s
                    if report:
                        self._stats['idle_s'] += idle_s
                    self.energy_remaining -= nrg.calc_idle_kwh(idle_s)
                    self.soc = self.energy_remaining/self.battery_capacity

                    if idle_s > 0:
                        idle_end = idle_start + idle_s
                        dispatch_start = idle_end
                        writer.writerow([self.veh_id, -1, idle_start, self.avail_lat, self.avail_lon, idle_end, self.avail_lat, self.avail_lon, 0, round(self.soc, 2), 0])
                else:
                    idle_s = inpt.MINUTES_BEFORE_CHARGE * 60
                    if report:
                        self._stats['idle_s'] += idle_s
                    self.energy_remaining -= nrg.calc_idle_kwh(idle_s)
                    self.soc = self.energy_remaining/self.battery_capacity
                    idle_end = idle_start + idle_s
                    refuel_start = idle_end
                    writer.writerow([self.veh_id, -1, idle_start, self.avail_lat, self.avail_lon, idle_end, self.avail_lat, self.avail_lon, 0, round(self.soc, 2), 0])

                    # Update w/ charging
                    pwr = inpt.UBIQUITOUS_CHARGER_POWER
                    secs_to_full = chrg.calc_const_charge_secs_to_full(self.energy_remaining, self.battery_capacity, kw=pwr)
                    if secs_to_full >= (diff_s - idle_s):
                        refuel_s = diff_s - idle_s
                        if report:
                            self._stats['refuel_s'] += refuel_s
                        self.energy_remaining = self.energy_remaining + chrg.calc_const_charge_kwh(refuel_s, kw=pwr)
                        self.soc = self.energy_remaining/self.battery_capacity
                        refuel_end = refuel_start + refuel_s
                        dispatch_start = refuel_end
                        if report:
                            self.refuel_cnt += 1
                        writer.writerow([self.veh_id, -3, refuel_start, self.avail_lat, self.avail_lon, refuel_end, self.avail_lat, self.avail_lon, 0, round(self.soc, 2), 0])
                    else:
                        refuel_s = secs_to_full
                        if report:
                            self._stats['refuel_s'] += refuel_s
                        self.energy_remaining = self.battery_capacity
                        self.soc = self.energy_remaining/self.battery_capacity
                        if refuel_s > 0:
                            refuel_end = refuel_start + refuel_s
                            idle2_start = refuel_end
                            if report:
                                self.refuel_cnt += 1
                            writer.writerow([self.veh_id, -3, refuel_start, self.avail_lat, self.avail_lon, refuel_end, self.avail_lat, self.avail_lon, 0, round(self.soc, 2), 0])

                        # Update w/ second idle event after charge to full
                        idle2_s = diff_s - idle_s - refuel_s
                        if report:
                            self._stats['idle_s'] += idle2_s
                        self.energy_remaining -= nrg.calc_idle_kwh(idle2_s)
                        self.soc = self.energy_remaining/self.battery_capacity
                        idle2_end = idle2_start + idle2_s
                        dispatch_start = idle2_end
                        writer.writerow([self.veh_id, -1, idle2_start, self.avail_lat, self.avail_lon, idle2_end, self.avail_lat, self.avail_lon, 0, round(self.soc, 2), 0])

            elif inpt.CHARGING_SCENARIO == 'Station': # NO ubiquitous charging assumption
                idle_start = self.avail_time
                idle_s = diff_s
                if report:
                    self._stats['idle_s'] += idle_s
                self.energy_remaining -= nrg.calc_idle_kwh(idle_s)
                self.soc = self.energy_remaining/self.battery_capacity
                if idle_s > 0:
                    idle_end = idle_start + idle_s
                    dispatch_start = idle_end
                    writer.writerow([self.veh_id, -1, idle_start, self.avail_lat, self.avail_lon, idle_end, self.avail_lat, self.avail_lon, 0, round(self.soc, 2), 0])

            # Update w/ dispatch
            if report:
                self._stats['dispatch_vmt'] += dispatch_dist
                self._stats['total_vmt'] += dispatch_dist

            if dispatch_dist > 0:
                dispatch_time_s = otime - dispatch_start
                if report:
                    self._stats['dispatch_s'] += dispatch_time_s
                self.energy_remaining -= nrg.calc_trip_kwh(dispatch_dist, dispatch_time_s, self._wh_per_mile_lookup)
                self.soc = self.energy_remaining/self.battery_capacity
                writer.writerow([self.veh_id, -2, dispatch_start, self.avail_lat, self.avail_lon, otime, olat, olon, dispatch_dist, round(self.soc, 2), 0])

            # Update w/ trip
            self.avail_lat = dlat
            self.avail_lon = dlon
            self.avail_time = dtime
            if report:
                self._stats['trip_vmt'] += trip_dist
                self._stats['total_vmt'] += trip_dist
            trip_time_s = dtime - otime
            if report:
                self._stats['trip_s'] += trip_time_s

            if trip_time_s > 0:
                self.energy_remaining -= nrg.calc_trip_kwh(trip_dist, trip_time_s, self._wh_per_mile_lookup)

            self.soc = self.energy_remaining / self.battery_capacity
            if report:
                self._stats['requests_filled'] += 1
                self._stats['passengers_delivered'] += passengers
            writer.writerow([self.veh_id, trip_id, otime, olat, olon, dtime, dlat, dlon, trip_dist, round(self.soc, 2), passengers])


    def refuel(self, charg_stations, final_soc, report):
        with open(self._log, 'a') as f:
            writer = csv.writer(f)

            # Locate nearest station
            nearest_station = charg_stations[0]
            dist_to_nearest = haversine((self.avail_lat, self.avail_lon), (nearest_station.lat, nearest_station.lon), unit='mi') * inpt.self._ENV['RN_SCALING_FACTOR']
            for station in charg_stations[1:]:
                dist = haversine((self.avail_lat, self.avail_lon), (station.lat, station.lon), unit='mi') * inpt.self._ENV['RN_SCALING_FACTOR']
                if dist < dist_to_nearest:
                    nearest_station = station
                    dist_to_nearest = dist

            # Dispatch to station
            if report:
                self._stats['dispatch_vmt'] += dist_to_nearest
                self._stats['total_vmt'] += dist_to_nearest

            if dist_to_nearest > 0:
                dispatch_time_s = dist_to_nearest / inpt.self._ENV['DISPATCH_MPH'] * 3600
                if report:
                    self._stats['dispatch_s'] += dispatch_time_s
                dispatch_start = self.avail_time
                dispatch_end = dispatch_start + dispatch_time_s
                self.energy_remaining -= nrg.calc_trip_kwh(dist_to_nearest, dispatch_time_s, self._wh_per_mile_lookup)
                self.soc = max(0, self.energy_remaining/self.battery_capacity)
                writer.writerow([self.veh_id, -2, dispatch_start, self.avail_lat, self.avail_lon, dispatch_end, nearest_station.lat, nearest_station.lon, dist_to_nearest, round(self.soc, 2), 0])

            # Charge at station
            self.avail_lat = nearest_station.lat
            self.avail_lon = nearest_station.lon
            soc_i = self.soc
            charge_time = chrg.query_charge_stats(self._charge_template, soc_i=soc_i*100, soc_f=final_soc*100)[2]
            if report:
                self._stats['refuel_s'] += charge_time
            start_time = dispatch_end
            end_time = dispatch_end + charge_time
            self.avail_time = end_time
            self.soc = final_soc
            self.energy_remaining = self.soc * self.battery_capacity
            if report:
                self.refuel_cnt += 1
            writer.writerow([self.veh_id, -3, start_time, self.avail_lat, self.avail_lon,
                             end_time, self.avail_lat, self.avail_lon, 0, self.soc, 0])
            nearest_station.add_recharge(self.veh_id, start_time, end_time, soc_i, final_soc)

    def check_vehicle_availability(self, req):
        """
        Checks if vehicle can fulfill request; This is dependent
        on availability (time-based), dispatch distance, and state
        of charge.
        """

        #TODO: Need to refactor the inpt constants.
        #IDEA: Move global constants to the main.csv/VEH.csv file. For variables
        #that change over the simulation, pass to this function via an input dict. -NR

        origin_time = req['origin_time']
        origin_lat = req['origin_lat']
        origin_lon = req['origin_lon']
        dest_time = req['dest_time']
        trip_dist = req['trip_dist']

        #TODO: the haversine calc is relatively expensive. We should return the
        # result to the simulation after this function is called.
        disp_dist = haversine((self.avail_lat, self.avail_lon), (origin_lat, origin_lon), unit='mi') * inpt.self._ENV['RN_SCALING_FACTOR']
        # check max dispatch constraint
        if disp_dist > self._ENV['MAX_DISPATCH_MILES']:
            return False

        disp_time_s = disp_dist/inpt.self._ENV['DISPATCH_MPH'] * 3600

        # check time constraint
        if self.avail_time + disp_time_s > origin_time:
            return False

        if disp_time_s > 0:
            disp_energy = nrg.calc_trip_kwh(disp_dist, disp_time_s, self._wh_per_mile_lookup)
        else:
            disp_energy = 0

        trip_time_s = dest_time - origin_time
        trip_energy = nrg.calc_trip_kwh(trip_dist, trip_time_s, self._wh_per_mile_lookup)

        total_dist = disp_dist + trip_dist
        total_energy = disp_energy + trip_energy

        # check hypothetical self.energy remaining
        if inpt.CHARGING_SCENARIO == 'Ubiq':
            refuel_s = origin_time - disp_time_s - self.avail_time
            pwr = inpt.UBIQUITOUS_CHARGER_POWER

            if refuel_s > inpt.MINUTES_BEFORE_CHARGE * 60:
                hyp_energy_remaining = self.energy_remaining + chrg.calc_const_charge_kwh(refuel_s, kw=pwr)
            else:
                hyp_energy_remaining = self.energy_remaining
        else:
            hyp_energy_remaining = self.energy_remaining

        if (hyp_energy_remaining - total_energy)/self.battery_capacity < self._ENV['MIN_ALLOWED_SOC']:
            return False

        return True
