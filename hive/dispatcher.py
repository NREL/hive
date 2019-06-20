"""
Dispatcher Object for high-level decision making in HIVE. Includes functions for
vehicle dispatching, and DCFC station/base selection.
"""

import datetime

from hive import tripenergy as nrg
from hive import charging as chrg
from hive import helpers as hlp

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

    def __init__(self, fleet, stations, bases, station_power_lookup, base_power_lookup):
        self._fleet = fleet
        self._stations = stations
        self._bases = bases

    def _reset_failure_tracking(self):
        """
        Resets internal failure type tracking log.
        """
        self.stats = {}
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
        disp_dist_mi = hlp.estimate_vmt(veh.avail_lat,
                                        veh.avail_lon,
                                        request['pickup_lat'],
                                        request['pickup_lon'],
                                        scaling_factor = veh.ENV['RN_SCALING_FACTOR'])
        disp_time_s = disp_dist_mi/veh.ENV['DISPATCH_MPH'] * 3600
        disp_start_time = request['pickup_time'] - datetime.timedelta(seconds=disp_time_s)
        disp_energy_kwh = nrg.calc_trip_kwh(disp_dist_mi, disp_time_s, veh.WH_PER_MILE_LOOKUP)
        
        idle_time_s = (disp_start_time - veh.avail_time).total_seconds()
        idle_time_min = idle_time_s / 60
        idle_energy_kwh = nrg.calc_idle_kwh(idle_time_s)

        trip_time_s = (request['dropoff_time'] - request['pickup_time']).total_seconds()
        trip_energy_kwh = nrg.calc_trip_kwh(request['distance_miles'], trip_time_s, veh.WH_PER_MILE_LOOKUP)
        
        total_energy_use_kwh = idle_energy_kwh + disp_energy_kwh + trip_energy_kwh
        hyp_energy_remaining = veh.energy_remaining - total_energy_use_kwh
        hyp_soc = hyp_energy_remaining / veh.BATTERY_CAPACITY

        calcs = {
            'idle_time_s': idle_time_s,
            'idle_energy_kwh': idle_energy_kwh,
            'refuel_energy_gained_kwh': energy_gained_kwh,
            'disp_dist_miles': disp_dist_mi,
            'disp_time_s': disp_time_s,
            'disp_start': disp_start_time, 
            'disp_energy_kwh': disp_energy_kwh,
            'trip_energy_kwh': trip_energy_kwh,
            'reserve': False
        }

        # Update Vehicles that should have charged at a station:
        if veh.soc < veh.ENV['LOWER_SOC_THRESH_STATION']:
            station, station_dist_mi = self._find_nearest_plug(veh, type='station')
            veh.refuel_at_station(station, station_dist_mi)

        # Check 1 - Vehicle is Active at Time of Request
        if idle_time_min > veh.ENV['MAX_ALLOWABLE_IDLE_MINUTES']:
            base, base_dist_mi = self._find_nearest_plug(veh, type='base')
            veh.return_to_base(base, base_dist_mi)
            base.avail_plugs -= 1
            return False, None

        # Check 2 - Max Dispatch Constraint Not Violated
        if disp_dist_mi > veh.ENV['MAX_DISPATCH_MILES']:
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
        disp_dist_mi = hlp.estimate_vmt(veh.avail_lat,
                                        veh.avail_lon,
                                        request['pickup_lat'],
                                        request['pickup_lon'],
                                        scaling_factor = veh.ENV['RN_SCALING_FACTOR'])
        disp_time_s = disp_dist_mi/veh.ENV['DISPATCH_MPH'] * 3600
        disp_energy_kwh = nrg.calc_trip_kwh(disp_dist_mi,
                                            disp_time_s,
                                            veh.WH_PER_MILE_LOOKUP)
        trip_time_s = (request['dropoff_time'] - request['pickup_time']).total_seconds()
        trip_energy_kwh = nrg.calc_trip_kwh(request['distance_miles'],
                                            trip_time_s,
                                            veh.WH_PER_MILE_LOOKUP)
        total_energy_use_kwh = disp_energy_kwh + trip_energy_kwh

        disp_start_time = request['pickup_time'] - datetime.timedelta(seconds=disp_time_s)
        refuel_s = (disp_start_time - veh.avail_time).total_seconds()

        if veh._base['plug_type'] == 'AC':
            kw = veh._base['kw']
            energy_gained_kwh = chrg.calc_const_charge_kwh(refuel_s, kw)

        elif veh._base['plug_type'] == 'DC':
            kw = veh._base['kw']
            energy_gained_kwh = chrg.calc_dcfc_kwh(veh.CHARGE_TEMPLATE,
                                                   veh.energy_remaining,
                                                   veh.BATTERY_CAPACITY,
                                                   kw,
                                                   refuel_s)
        
        battery_charge = veh.energy_remaining + energy_gained_kwh
        if battery_charge > veh.BATTERY_CAPACITY:
            reserve=True
            battery_charge = veh.BATTERY_CAPACITY
        else:
            reserve=False
                       
        hyp_energy_remaining = battery_charge - total_energy_use_kwh
        hyp_soc = hyp_energy_remaining / veh.BATTERY_CAPACITY

        calcs = {
            'idle_time_s': None,
            'idle_energy_kwh': None,
            'refuel_energy_gained_kwh': energy_gained_kwh,
            'disp_dist_miles': disp_dist_mi,
            'disp_time_s': disp_time_s,
            'disp_start': disp_start_time, 
            'disp_energy_kwh': disp_energy_kwh,
            'trip_energy_kwh': trip_energy_kwh,
            'reserve': reserve
        }

        # Check 1 - Time Constraint Not Violated
        if (veh.avail_time!=0) and \
        (veh.avail_time + datetime.timedelta(seconds=disp_time_s) > request['pickup_time']):
            self.stats['failure_inactive_time']+=1
            return False, None

        # Check 2 - Battery Constraint Not Violated
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
                dist_mi = hlp.estimate_vmt(veh.avail_lat,
                                           veh.avail_lon,
                                           station.LAT,
                                           station.LON,
                                           scaling_factor = veh.ENV['RN_SCALING_FACTOR'])
                if (nearest == None) and (dist_to_nearest == None):
                    nearest = station
                    dist_to_nearest = dist_mi
                else:
                    if dist_mi < dist_to_nearest:
                        nearest = station
                        dist_to_nearest = dist_mi

        return nearest, dist_to_nearest

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
                self._reset_failure_tracking()
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
                #TODO: Write failure log to CSV <-- STATUS bb
