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
        self.MAX_CHARGE_ACCEPTANCE_KW = max_charge_acceptance
        self.WH_PER_MILE_LOOKUP = whmi_lookup
        self.CHARGE_TEMPLATE = charge_template

        # Public variables
        self.active = False
        self.avail_lat = None
        self.avail_lon = None
        self.base = None
        self.avail_time = None
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
            self.stats['pct_time_trip'] = self.stats['request_s'] / (self.stats['station_refuel_s'] \
                + self.stats['idle_s'] + self.stats['dispatch_s'] + self.stats['request_s'] + self.stats['base_refuel_s'])
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

        if self.active == False: # Vehicle previously inactive:
            base_refuel_start_time = calcs['base_refuel_start_time']
            base_refuel_end_time = calcs['base_refuel_end_time']
            base_refuel_s = calcs['base_refuel_s']
            base_refuel_energy_kwh = calcs['base_refuel_energy_kwh']
            base_reserve_start_time = calcs['base_reserve_start_time']
            base_reserve_end_time = calcs['base_reserve_end_time']
            disp_start_time = calcs['dispatch_start_time']
            disp_end_time = calcs['dispatch_end_time']
            disp_time_s = calcs['dispatch_time_s']
            disp_energy_kwh = calcs['dispatch_energy_kwh']
            disp_dist_mi = calcs['dispatch_dist_miles']
            req_energy_kwh = calcs['request_energy_kwh']
            reserve = calcs['reserve']

            # 1. Add VehicleBase refuel event & reserve event (if applicable)
            self.energy_remaining += base_refuel_energy_kwh
            self.soc = self.energy_remaining/self.BATTERY_CAPACITY
            #refuel event
            write_log({
                'veh_id': self.ID,
                'activity': 'refuel-base',
                'start_time': base_refuel_start_time,
                'start_lat': self.avail_lat,
                'start_lon': self.avail_lon,
                'end_time': base_refuel_end_time,
                'end_lat': self.avail_lat,
                'end_lon': self.avail_lon,
                'dist_mi': 0.0,
                'end_soc': round(self.soc, 2),
                'passengers': 0
            },
            self._LOG_COLUMNS,
            self._logfile)

            self.stats['base_refuel_cnt']+=1
            self.stats['base_refuel_s']+=base_refuel_s
            self.stats['refuel_energy_kwh']+=base_refuel_energy_kwh

            if reserve:
                #reserve event
                write_log({
                    'veh_id': self.ID,
                    'activity': 'reserve-base',
                    'start_time': base_reserve_start_time,
                    'start_lat': self.avail_lat,
                    'start_lon': self.avail_lon,
                    'end_time': base_reserve_end_time,
                    'end_lat': self.avail_lat,
                    'end_lon': self.avail_lon,
                    'dist_mi': 0.0,
                    'end_soc': round(self.soc, 2),
                    'passengers': 0
                },
                self._LOG_COLUMNS,
                self._logfile)

                base_reserve_s = (base_reserve_end_time - base_reserve_start_time).total_seconds()
                self.stats['base_reserve_s']+=base_reserve_s

            # 2. Add dispatch to pickup location
            self.energy_remaining-=disp_energy_kwh
            self.soc = self.energy_remaining / self.BATTERY_CAPACITY

            write_log({
                'veh_id': self.ID,
                'activity': 'dispatch-pickup',
                'start_time': disp_start_time,
                'start_lat': self.avail_lat,
                'start_lon': self.avail_lon,
                'end_time': disp_end_time,
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
            self.energy_remaining-=req_energy_kwh
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
            req_time_s = (request['dropoff_time'] - request['pickup_time']).total_seconds()
            self.stats['request_s']+=req_time_s
            self.active = True
            self._base = None
            self.avail_time = request['dropoff_time']
            self.avail_lat = request['dropoff_lat']
            self.avail_lon = request['dropoff_lon']

        else: # Vehicle previously inactive:
            idle_start_time = calcs['idle_start_time']
            idle_end_time = calcs['idle_end_time']
            idle_time_s = calcs['idle_time_s']
            idle_energy_kwh = calcs['idle_energy_kwh']
            disp_start_time = calcs['dispatch_start_time']
            disp_end_time = calcs['dispatch_end_time']
            disp_time_s = calcs['dispatch_time_s']
            disp_end_time = calcs['dispatch_end_time']
            disp_time_s = calcs['dispatch_time_s']
            disp_energy_kwh = calcs['dispatch_energy_kwh']
            disp_dist_mi = calcs['dispatch_dist_miles']
            req_energy_kwh = calcs['request_energy_kwh']


            # 1. Add idle event (if appropriate)
            if idle_time_s > 0:
                self.energy_remaining-=idle_energy_kwh
                self.soc = self.energy_remaining / self.BATTERY_CAPACITY

                write_log({
                    'veh_id': self.ID,
                    'activity': 'idle',
                    'start_time': idle_start_time,
                    'start_lat': self.avail_lat,
                    'start_lon': self.avail_lon,
                    'end_time': idle_end_time,
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
                'start_time': disp_start_time,
                'start_lat': self.avail_lat,
                'start_lon': self.avail_lon,
                'end_time': disp_end_time,
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
            self.energy_remaining-=req_energy_kwh
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
            request_s = (request['dropoff_time'] - request['pickup_time']).total_seconds()
            self.stats['request_s']+=request_s
            self.avail_time = request['dropoff_time']
            self.avail_lat = request['dropoff_lat']
            self.avail_lon = request['dropoff_lon']


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
        disp_mi = dist_mi
        disp_s = disp_mi / self.ENV['DISPATCH_MPH'] * 3600
        disp_end = self.avail_time + datetime.timedelta(seconds=disp_s)
        disp_energy_kwh = nrg.calc_trip_kwh(disp_mi,
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
            'dist_mi': disp_mi,
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
        kw = station.PLUG_POWER_KW
        soc_i = self.energy_remaining
        if station.PLUG_TYPE == 'AC':
            refuel_s = chrg.calc_const_charge_secs(soc_i,
                                                   self.ENV['UPPER_SOC_THRESH_STATION'],
                                                   kw)
        elif station.PLUG_TYPE == 'DC':
            refuel_s = chrg.calc_dcfc_secs(self.CHARGE_TEMPLATE,
                                          soc_i,
                                          self.ENV['UPPER_SOC_THRESH_STATION'],
                                          kw,
                                          soc_f = 1.0)

        refuel_start = self.avail_time
        refuel_end = refuel_start + datetime.timedelta(seconds=refuel_s)
        refuel_energy_kwh = self.BATTERY_CAPACITY * (self.ENV['UPPER_SOC_THRESH_STATION'] - self.soc)

        self.energy_remaining = self.BATTERY_CAPACITY * self.ENV['UPPER_SOC_THRESH_STATION']
        soc_f = self.energy_remaining / self.BATTERY_CAPACITY
        self.soc = soc_f

        write_log({
            'veh_id': self.ID,
            'activity': 'refuel-station',
            'start_time': refuel_start,
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

        # Update FuelStation
        station.add_charge_event(self, refuel_start, refuel_end, soc_i, soc_f, refuel_energy_kwh)

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
            'activity': 'idle',
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
        disp_mi = dist_mi
        disp_s = disp_mi / self.ENV['DISPATCH_MPH'] * 3600
        disp_end = self.avail_time + datetime.timedelta(seconds=disp_s)
        disp_energy_kwh = nrg.calc_trip_kwh(disp_mi,
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
            'dist_mi': disp_mi,
            'end_soc': round(self.soc, 2),
            'passengers': 0
            },
            self._LOG_COLUMNS,
            self._logfile)

        self.stats['dispatch_s'] += disp_s
        self.stats['dispatch_vmt'] += disp_mi
        self.stats['total_vmt'] += disp_mi
        self.active = False
        self.base = base
        self.avail_lat = base.LAT
        self.avail_lon = base.LON
        self.avail_time = disp_end

        # Update VehicleBase
        base.avail_plugs-=1
