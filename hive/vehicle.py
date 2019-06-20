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
            'request_vmt', #miles w/ 1+ passenger
            'dispatch_vmt', #empty miles
            'total_vmt', #total miles
            'requests_filled',
            'passengers_delivered',
            'base_refuel_cnt', #number of refuel/recharge events at a VehicleBase
            'station_refuel_cnt', #number of refuel/recharge events at a FuelStation
            'base_refuel_s', #seconds where a vehicle is inactive & charging at a VehicleBase
            'station_refuel_s', #seconds where a vehicle is active & charging at a FuelStation
            'refuel_energy_kwh' #kWh of charging
            'idle_s', #seconds where vehicle is active but is not moving (waiting for next action)
            'dispatch_s', #seconds where vehicle is active & traveling w/ 0 passengers
            'base_reserve_s', #seconds where vehicle is inactive & is in reserve
            'request_s', #seconds where vehicle is active & is serving a trip request
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
                max_charge_acceptance,
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

        self._logfile = logfile

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

    def __repr__(self):
        return str(f"Vehicle(id: {self.ID}, name: {self.NAME})")

    def dump_stats(self, filepath):
        self.stats['end_soc'] = self.soc

        try:
            self.stats['pct_time_trip'] = self.stats['trip_s'] / (self.stats['refuel_s'] \
                + self.stats['idle_s'] + self.stats['dispatch_s'] + self.stats['trip_s'])
        except ZeroDivisionError:
            self.stats['pct_time_trip'] = 0

        write_log(self.stats, self._STATS, filepath)

    def make_trip(self, request, calcs):
        """
        Function that completes a ride request.

        Updates Vehicle & logging with inter-trip idle, dispatch to pickup
        location, and completion of the provided request. Function requires a
        dictionary, calcs, of precomputed values from the Dispatcher used when 
        assessing the vehicle's viability.

        Parameters
        ----------
        request: dict
            Dictionary of parameters related to the specific request
        calcs: dict
            Dictionary of additional metrics precomputed by the hive.Dispatcher
            object when assessing the vehicle's viability for fulfilling request

        Returns
        -------
        None
        """
        # Unpack calcs
        idle_time_s = calcs['idle_time_s']
        idle_energy_kwh = calcs['idle_energy_kwh']
        refuel_energy_kwh = calcs['refuel_energy_gained_kwh']
        disp_dist_mi = calcs['disp_dist_mi']
        disp_time_s = calcs['disp_time_s']
        disp_start = cals['disp_start']
        disp_energy_kwh = calcs['disp_energy_kwh']
        trip_energy_kwh = calcs['trip_energy_kwh']
        reserve = calcs['reserve']

        if self.active == False: #veh prev inactive
            # 1. Add VehicleBase refuel event & reserve event (if applicable)
            if reserve: #vehicle was put in reserve
                #base refuel event
                if self._base['plug_type'] == 'AC':
                    kw = self._base['kw']
                    refuel_s = chrg.calc_const_charge_secs(self.energy_remaining, 
                                                           self.BATTERY_CAPACITY,
                                                           kw)
                elif self._base['plug_type'] == 'DC':
                    kw = self._base['kw']
                    refuel_s = chrg.calc_dcfc_secs(self.CHARGE_TEMPLATE, #Q: Does the charge template account for max charge acceptance?
                                                   self.energy_remaining,
                                                   self.BATTERY_CAPACITY,
                                                   kw,
                                                   soc_f = 1.0)
                refuel_end = veh.avail_time + datetime.timedelta(seconds=refuel_s)
                self.energy_remaining = self.BATTERY_CAPACITY
                self.soc = self.energy_remaining/self.BATTERY_CAPACITY

                write_log({
                    'veh_id': self.ID,
                    'activity': 'refuel-base',
                    'start_time': self.avail_time,
                    'start_lat': self.avail_lat,
                    'start_lon': self.avail_lon,
                    'end_time': refuel_end,
                    'end_lat': self.avail_lat,
                    'end_lon': self.avail_lon,
                    'dist_mi': 0.0,
                    'end_soc': round(self.soc, 2),
                    'passengers': 0
                },
                self._LOG_COLUMNS,
                self._logfile)

                self.stats['base_refuel_cnt']+=1
                self.stats['base_refuel_s']+=refuel_s
                self.stats['refuel_energy_kwh']+=refuel_energy_kwh

                #reserve event
                reserve_s = (dispatch_start - refuel_end).total_seconds()
                write_log({
                    'veh_id': self.ID,
                    'activity': 'reserve-base',
                    'start_time': refuel_end,
                    'start_lat': self.avail_lat,
                    'start_lon': self.avail_lon,
                    'end_time': disp_start,
                    'end_lat': self.avail_lat,
                    'end_lon': self.avail_lon,
                    'dist_mi': 0.0,
                    'end_soc': round(self.soc, 2),
                    'passengers': 0
                },
                self._LOG_COLUMNS,
                self._logfile)

                self.stats['base_reserve_s']+=reserve_s

            else: #vehicle was not put in reserve
                #base refuel event
                refuel_s = (disp_start - self.avail_time).total_seconds()
                
                self.energy_remaining+=refuel_energy_kwh
                self.soc = self.energy_remaining / self.BATTERY_CAPACITY

                write_log({
                    'veh_id': self.ID,
                    'activity': 'refuel-base'
                    'start_time': self.avail_time,
                    'start_lat': self.avail_lat,
                    'start_lon': self.avail_lon,
                    'end_time': disp_start,
                    'end_lat': self.avail_lat,
                    'end_lon': self.avail_lon,
                    'dist_mi': 0.0,
                    'end_soc': round(self.soc, 2),
                    'passengers': 0
                },
                self._LOG_COLUMNS,
                self._logfile)

                self.stats['base_refuel_cnt']+=1
                self.stats['base_refuel_s']+=refuel_s
                self.stats['refuel_energy_kwh']+=refuel_energy_kwh           

            # 2. Add dispatch to pickup location
            self.energy_remaining-=disp_energy_kwh
            self.soc = self.energy_remaining / self.BATTERY_CAPACITY

            write_log({
                'veh_id': self.ID,
                'activity': 'dispatch-pickup',
                'start_time': disp_start,
                'start_lat': self.avail_lat,
                'start_lon': self.avail_lon,
                'end_time': request['pickup_time'],
                'end_lat': request['pickup_lat'],
                'end_lon': request['pickup_lon'],
                'dist_mi': disp_dist_mi,
                'end_soc': round(self.soc, 2),
                'passengers': 0
            },
            self._LOG_COLUMNS,
            self._logfile)

            self.stats['dispatch_vmt']+=disp_dist_mi
            self.stats['total_vmt']+=disp_dist_mi
            self.stats['dispatch_s']+=disp_time_s

            # 3. Add request
            request_s = (request['dropoff_time'] - request['pickup_time']).total_seconds()
            self.energy_remaining-=trip_energy_kwh
            self.soc = self.energy_remaining / self.BATTERY_CAPACITY

            write_log({
                'veh_id': self.ID,
                'activity': 'request',
                'start_time': request['pickup_time'],
                'start_lat': request['pickup_lat'],
                'start_lon': request['pickup_lon'],
                'end_time': request['dropoff_time'],
                'end_lat': request['dropoff_lat'],
                'end_lon': request['dropoff_lon'],
                'dist_mi': request['distance_miles'],
                'end_soc': round(self.soc, 2),
                'passengers': request['passengers']
            },
            self._LOG_COLUMNS,
            self._logfile)

            self.stats['request_vmt']+=request['distance_miles']
            self.stats['total_vmt']+=request['distance_miles']
            self.stats['requests_filled']+=1
            self.stats['passengers_delivered']+=request['passengers']
            self.stats['request_s']+=request_s
            self.active = True
            self.base = None
            self.avail_time = request['dropoff_time']
            self.avail_lat = request['dropoff_lat']
            self.avail_lon = request['dropoff_lon']

            #TODO - Update VehicleBase object w/ charge event information

        else: #veh prev active
            # 1. Add idle event (if appropriate)
            if idle_time_s > 0:              
                self.energy_remaining-=idle_energy_kwh
                self.soc = self.energy_remaining / self.BATTERY_CAPACITY
                
                write_log({
                    'veh_id': self.ID,
                    'activity': 'idle',
                    'start_time': self.avail_time,
                    'start_lat': self.avail_lat,
                    'start_lon': self.avail_lon,
                    'end_time': disp_start,
                    'end_lat': self.avail_lat,
                    'end_lon': self.avail_lon,
                    'dist_mi': 0.0,
                    'end_soc': round(self.soc,2),
                    'passengers': 0
                },
                self._LOG_COLUMNS,
                self._logfile)

                self.stats['idle_s'] += idle_time_s

            # 2. Add dispatch to pickup location
            self.energy_remaining-=disp_energy_kwh
            self.soc = self.energy_remaining / self.BATTERY_CAPACITY

            write_log({
                'veh_id': self.ID,
                'activity': 'dispatch-pickup',
                'start_time': disp_start,
                'start_lat': self.avail_lat,
                'start_lon': self.avail_lon,
                'end_time': request['pickup_time'],
                'end_lat': request['pickup_lat'],
                'end_lon': request['pickup_lon'],
                'dist_mi': disp_dist_mi,
                'end_soc': round(self.soc, 2),
                'passengers': 0
            },
            self._LOG_COLUMNS,
            self._logfile)

            self.stats['dispatch_vmt']+=disp_dist_mi
            self.stats['total_vmt']+=disp_dist_mi
            self.stats['dispatch_s']+=disp_time_s

            # 3. Add request
            request_s = (request['dropoff_time'] - request['pickup_time']).total_seconds()
            self.energy_remaining-=trip_energy_kwh
            self.soc = self.energy_remaining / self.BATTERY_CAPACITY

            write_log({
                'veh_id': self.ID,
                'activity': 'request',
                'start_time': request['pickup_time'],
                'start_lat': request['pickup_lat'],
                'start_lon': request['pickup_lon'],
                'end_time': request['dropoff_time'],
                'end_lat': request['dropoff_lat'],
                'end_lon': request['dropoff_lon'],
                'dist_mi': request['distance_miles'],
                'end_soc': round(self.soc, 2),
                'passengers': request['passengers']
            },
            self._LOG_COLUMNS,
            self._logfile)

            self.stats['request_vmt']+=request['distance_miles']
            self.stats['total_vmt']+=request['distance_miles']
            self.stats['requests_filled']+=1
            self.stats['passengers_delivered']+=request['passengers']
            self.stats['request_s']+=request_s
            self.avail_time = request['dropoff_time']
            self.avail_lat, = request['dropoff_lat']
            self.avail_lon = request['dropoff_lon']

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

    def refuel_at_station(self, station, dist_mi):
        """
        Function to send Vehicle to FuelStation for refuel event.

        Sends Vehicle to FuelStation station and updates vehicle reporting 
        logs/attributes with a dispatch event and charging event.

        Paramters
        ---------
        station: hive.stations.FuelStation
            hive FuelStation object assigned to Vehicle
        dist_mi: double precision
            Approx. driving distance to station

        Returns
        -------
        None
        """
        # 1. Add dispatch to station
        disp_s = dist_mi / self.ENV['DISPATCH_MPH'] * 3600
        disp_end = self.avail_time + datetime.timedelta(seconds=disp_s)
        disp_energy_kwh = nrg.calc_trip_kwh(dist_mi,
                                            disp_s,
                                            self.WH_PER_MILE_LOOKUP)
        self.energy_remaining -= disp_energy_kwh
        self.soc = self.energy_remaining/self.BATTERY_CAPACITY

        write_log({
            'veh_id': self.ID,
            'activity': 'dispatch-station',
            'start_time': self.avail_time,
            'start_lat': self.avail_lat,
            'start_lon': self.avail_lon,
            'end_time': disp_end,
            'end_lat': station.LAT,
            'end_lon': station.LON,
            'dist_mi': dist_mi,
            'end_soc': round(self.soc, 2),
            'passengers': 0
            },
            self._LOG_COLUMNS,
            self._logfile)

        self.stats['dispatch_s'] += disp_s
        self.stats['dispatch_vmt'] += disp_mi
        self.stats['total_vmt'] += disp_mi
        self.avail_time = disp_end
        self.avail_lat = station.LAT
        self.avail_lon = station.LON

        # 2. Add station recharge
        kw = station.plug_power
        if station.plug_type == 'AC':
            refuel_s = chrg.calc_const_charge_secs(self.energy_remaining, 
                                                   self.ENV['UPPER_SOC_THRESH_STATION'],
                                                   kw)
        elif station.plug_type == 'DC':
            refuel_s = chrg.calc_dcfc_secs(self.CHARGE_TEMPLATE,
                                          self.energy_remaining,
                                          self.ENV['UPPER_SOC_THRESH_STATION'],
                                          kw,
                                          soc_f = 1.0)

        refuel_end = self.avail_time + datetime.timedelta(seconds=refuel_s)
        refuel_energy_kwh = self.BATTERY_CAPACITY * (self.ENV['UPPER_SOC_THRESH_STATION'] - self.soc)

        self.energy_remaining = self.BATTERY_CAPACITY * self.ENV['UPPER_SOC_THRESH_STATION']
        self.soc = self.energy_remaining / self.BATTERY_CAPACITY

        write_log({
            'veh_id': self.ID,
            'activity': 'refuel-station'
            'start_time': self.avail_time,
            'start_lat': self.avail_lat,
            'start_lon': self.avail_lon,
            'end_time': refuel_end,
            'end_lat': self.avail_lat,
            'end_lon': self.avail_lon,
            'dist_mi': 0.0,
            'end_soc': round(self.soc, 2),
            'passengers': 0
        },
        self._LOG_COLUMNS,
        self._logfile)

        self.stats['station_refuel_cnt']+=1
        self.stats['station_refuel_s']+=refuel_s
        self.stats['refuel_energy_kwh']+=refuel_energy_kwh  
        self.avail_time = refuel_end  

    def return_to_base(self, base, dist_mi):
        """
        Function to send Vehicle to VehicleBase.

        Sends Vehicle to VehicleBase base and updates vehicle reporting
        logs/attributes with an idle event and the dispatch event. As a result,
        Vehicle "active" flag is flipped to False.

        Parameters
        ----------
        base: hive.stations.VehicleBase
            hive VehicleBase object assigned to Vehicle
        dist_mi: double precision
            Approx. driving distance to base

        Returns
        -------
        None
        """

        # 1. Add idle event
        idle_s = self.ENV['MAX_ALLOWABLE_IDLE_MINUTES'] * 60
        idle_end = self.avail_time + datetime.timedelta(seconds=idle_s)
        idle_energy_kwh = nrg.calc_idle_kwh(idle_s)
        self.energy_remaining-=idle_energy_kwh
        self.soc = self.energy_remaining / self.BATTERY_CAPACITY
        
        write_log({
            'veh_id': self.ID,
            'activity': 'idle'
            'start_time': self.avail_time,
            'start_lat': self.avail_lat,
            'start_lon': self.avail_lon,
            'end_time': idle_end,
            'end_lat': self.avail_lat,
            'end_lon': self.avail_lon,
            'dist_mi': 0.0,
            'end_soc': round(self.soc, 2),
            'passengers': 0
        },
        self._LOG_COLUMNS,
        self._logfile)

        self.stats['idle_s'] += idle_s
        self.avail_time = idle_end

        # 2. Add dispatch to base
        disp_s = dist_mi / self.ENV['DISPATCH_MPH'] * 3600
        disp_end = self.avail_time + datetime.timedelta(seconds=disp_s)
        disp_energy_kwh = nrg.calc_trip_kwh(dist_mi,
                                            disp_s,
                                            self.WH_PER_MILE_LOOKUP)
        self.energy_remaining -= disp_energy_kwh
        self.soc = self.energy_remaining/self.BATTERY_CAPACITY

        write_log({
            'veh_id': self.ID,
            'activity': 'dispatch-base',
            'start_time': self.avail_time,
            'start_lat': self.avail_lat,
            'start_lon': self.avail_lon,
            'end_time': disp_end,
            'end_lat': base.LAT,
            'end_lon': base.LON,
            'dist_mi': dist_mi,
            'end_soc': round(self.soc, 2),
            'passengers': 0
            },
            self._LOG_COLUMNS,
            self._logfile)

        self.stats['dispatch_s'] += disp_s
        self.stats['dispatch_vmt'] += disp_mi
        self.stats['total_vmt'] += disp_mi
        self.active = False
        base_lookup = {'base_id': base.base_id,
                       'plug_type': base.PLUG_TYPE,
                       'kw': base.PLUG_POWER}
        self._base = base_lookup
        self.avail_lat = base.LAT
        self.avail_lon = base.LON
        self.avail_time = disp_end   
