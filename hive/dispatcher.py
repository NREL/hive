"""
Dispatcher Object for high-level decision making in HIVE. Includes functions for
vehicle dispatching, and DCFC station/base selection.
"""

import datetime
from haversine import haversine

from hive import tripenergy as nrg
from hive import charging as chrg

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
        'failure_inactive_time',
        'failure_inactive_battery',
    ]

    def __init__(self, fleet, stations, bases):
        self._fleet = fleet
        self._stations = stations
        self._bases = bases

        self.stats = dict()
        for stat in self._STATS:
            self.stats[stat] = 0

    def _check_active_viability(self, veh, request):
        """
        Checks if active vehicle can fulfill request w/o violating several
        constraints. Function requires a hive.Vehicle object and a trip request
        Function returns a boolean indicating the ability of the vehicle to service
        the request and the updated failure log. This function also sends vehicles
        exceeding the MAX_WAIT_TIME_MINUTES constraint to a base for charging.
        """

        assert veh.active==True, "Vehicle is not active!"

        # Calculations
        disp_dist_miles = haversine((veh.avail_lat, veh.avail_lon),
                                (request['pickup_lat'], request['pickup_lon']), unit='mi') \
                                * veh.ENV['RN_SCALING_FACTOR']
        disp_time_s = disp_dist/veh.ENV['DISPATCH_MPH'] * 3600
        idle_time_s = ((request['pickup_time'] - datetime.timedelta(seconds=disp_time_s)) \
        - veh.avail_time).total_seconds()
        idle_time_min = idle_time_s / 60
        disp_energy_kwh = nrg.calc_trip_kwh(disp_dist, disp_time_s, veh.WH_PER_MILE_LOOKUP)
        trip_time_s = (request['dropoff_time'] - request['pickup_time']).total_seconds()
        trip_energy_kwh = nrg.calc_trip_kwh(request['distance_miles'], trip_time_s, veh.WH_PER_MILE_LOOKUP)
        total_energy_kwh = disp_energy_kwh + trip_energy_kwh
        hyp_energy_remaining = veh.energy_remaining - total_energy_kwh
        hyp_soc = hyp_energy_remaining / veh.BATTERY_CAPACITY

        calcs = {
            'disp_dist_miles': disp_dist_miles,
            'disp_time_s': disp_time_s,
            'idle_time_s': idle_time_s,
            'battery_kwh_remains': hyp_energy_remaining,
        }
        
        # Check 1 - Vehicle is Active at Time of Request
        if idle_time_min > veh.ENV['MAX_WAIT_TIME_MINUTES']:
            base = self._find_nearest_plug(veh, type='base')
            veh.return_to_base(base)
            base.avail_plugs -= 1
            return False, None

        # Check 2 - Max Dispatch Constraint Not Violated
        if disp_dist_miles > veh.ENV['MAX_DISPATCH_MILES']:
            self.stats['failure_active_max_dispatch']+=1
            return False, None

        # Check 3 - Time Constraint Not Violated
        if veh.avail_time + datetime.timedelta(seconds=disp_time_s) > request['pickup_time']:
            self.stats['failure_active_time']+=1
            return False, None

        # Check 4 - Battery Constraint Not Violated
        if hyp_soc < veh.ENV['MIN_ALLOWED_SOC']:
            self.stats['failure_active_battery']+=1
            return False, None

        # Check 5 - Max Occupancy Constraint Not Violated
        if request['passengers'] > veh.avail_seats:
            self.stats['failure_active_seats']+=1
            return False, None

        return True, calcs

    def _check_inactive_viability(self, veh, request):
        """
        Checks if inactive vehicle can fulfill request w/o violating several
        constraints. Function requires a hive.Vehicle object and a trip request.
        Function returns a boolean indicating the ability
        of the vehicle to service the request. If the vehicle is able to service
        the request, a dict w/ calculated values are passed as output to avoid
        recalculation in the hive.Vehicle.make_trip method.
        """
        assert veh.active!=True, "Vehicle is active!"

        # Calculations
        disp_dist_miles = haversine((veh.avail_lat, veh.avail_lon),
                                (request['pickup_lat'], request['pickup_lon']), unit='mi') \
                                * veh.ENV['RN_SCALING_FACTOR']
        disp_time_s = disp_dist/veh.ENV['DISPATCH_MPH'] * 3600
        disp_energy_kwh = nrg.calc_trip_kwh(disp_dist, disp_time_s, veh.WH_PER_MILE_LOOKUP)
        trip_time_s = (request['dropoff_time'] - request['pickup_time']).total_seconds()
        trip_energy_kwh = nrg.calc_trip_kwh(request['distance_miles'], trip_time_s, veh.WH_PER_MILE_LOOKUP)
        total_energy_kwh = disp_energy_kwh + trip_energy_kwh
        
        energcalc_const_charge_kwh(time_s, kw=7.2):
    """Function needs docstring"""
    kwh = kw * (time_s / 3600.0)
    
    return kwh
        energy_gained_kwh = chrg.query_charge_stats(veh.CHARGE_TEMPLATE, veh.soc, charge_time=-1, soc_f=-1)

        # TODO: Account for time spent charging at a base in hyp_energy_remaining calc
        hyp_energy_remaining = veh.energy_remaining - total_energy_kwh
        hyp_soc = hyp_energy_remaining / veh.BATTERY_CAPACITY

        calcs = {
            'disp_dist_miles': disp_dist_miles,
            'disp_time_s': disp_time_s,
            'battery_kwh_remains': hyp_energy_remaining,
        }
        
        # Check 1 - Time Constraint Not Violated
        if (veh.avail_time!=0) and (veh.avail_time + datetime.timedelta(seconds=disp_time_s) > request['pickup_time']):
            self.stats['failure_inactive_time']+=1
            return False, None

        # Check 2 - Battery Constraint Not Violated
        for base in self._bases:
            if veh.avail_lat == base.LAT and veh.avail_lon == base.LON:
                charge_type = base.PLUG_TYPE
                charge_power = base.PLUG_POWER
                break

        #TODO: Refactor charging.py for single function that accepts charge_type,
        ##charge power, time, and considers max_acceptance, returning soc_f
        ###then: hyp_energy_remaining = (self.battery_capacity * soc_f) - total_energy
        hyp_energy_remaining = 0

        if hyp_soc < veh.ENV['MIN_ALLOWED_SOC']:
            self.stats['failure_inactive_battery']+=1
            return False, None

        # Check 3 - Max Occupancy Constraint Not Violated
        if request['passengers'] > veh.avail_seats:
            self.stats['failure_inactive_seats']+=1
            return False, None

        return True, calcs

    def _find_nearest_plug(self, veh, type='station'):
        """
        Function takes hive.vehicle.Vehicle object and returns the FuelStation 
        nearest Vehicle with at least one available plug. The "type" argument 
        accepts either 'station' or 'base', informing the search space.
        """
        #IDEA: Store stations in a geospatial index to eliminate exhaustive search. -NR
        nearest, dist_to_nearest = None, None

        assert type in ['station', 'base'], """"type" must be either 'station' 
        or 'base'."""
        
        if type == 'station':
            stations = self._stations
        elif type == 'base':
            stations = self._bases

        for station in stations: 
            if station.avail_plugs != 0:
                dist = haversine((veh.avail_lat, veh.avail_lon),
                                (station.LAT, station.LON), unit='mi') \
                                * veh.ENV['RN_SCALING_FACTOR']
                if (nearest == None) and (dist_to_nearest == None):
                    nearest = station
                    dist_to_nearest = dist
                else:
                    if dist < dist_to_nearest:
                        nearest = station
                        dist_to_nearest = dist

        return nearest

    def process_requests(self, requests):
        """
        process_requests is called for each simulation time step.

        Inputs
        ------
        requests - one or many requests to distribute to the fleet.
        """
        #Catch single requests.
        if type(requests) != type(list()):
            requests = [requests]

        for req in requests:
            req_filled = False #default
            for veh in self._fleet:
                # Check active vehicles in fleet
                if veh.active:
                    viable, calcs = self._check_active_viability(veh, req)
                    if viable:
                        veh.make_trip(req, calcs)
                        self._fleet.remove(veh) #pop veh from queue
                        self._fleet.append(veh) #append veh to end of queue
                        req_filled = True
                        break
            if not req_filled:
                #TODO: Remove break when check_inactive_viability() is completed.
                break
                for veh in self._fleet:
                    # Check inactive (base) vehicles in fleet
                    if not veh.active:
                        viable, calcs = self._check_inactive_viability(veh, req)
                        if viable:
                            veh.make_trip(req, calcs)
                            self._fleet.remove(veh) #pop veh from queue
                            self._fleet.append(veh) #append veh to end of queue
                            req_filled = True
                            break
            if not req_filled:
                 write_log({
                    'start_time': self.avail_time,
                    'start_lat': self.avail_lat,
                    'start_lon': self.avail_lon,
                    'end_time': dtime,
                    'end_lat': base.LAT,
                    'end_lon': base.LON,
                    'dist_mi': dispatch_dist,
                    'end_soc': round(self.soc, 2),
                    'passengers': 0
                    },
            self._LOG_COLUMNS,
            self._logfile)
            pass
            #TODO: Write failure log to CSV
