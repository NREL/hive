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
                stations,
                bases,
                failed_requests_log
                ):

        self._inactive_fleet = fleet
        self._active_fleet = []
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
        disp_dist_mi = hlp.estimate_vmt_2D(veh.x,
                                        veh.y,
                                        request.pickup_x,
                                        request.pickup_y,
                                        scaling_factor = veh.ENV['RN_SCALING_FACTOR'])
        disp_time_s = disp_dist_mi/veh.ENV['DISPATCH_MPH'] * 3600
        disp_end_time = request.pickup_time
        disp_start_time = disp_end_time - datetime.timedelta(seconds=disp_time_s)
        disp_energy_kwh = nrg.calc_trip_kwh(disp_dist_mi,
                                            disp_time_s,
                                            veh.WH_PER_MILE_LOOKUP)

        idle_start_time = veh.avail_time
        idle_end_time = disp_start_time
        idle_time_s = (idle_end_time - idle_start_time).total_seconds()
        idle_time_min = idle_time_s / 60
        idle_energy_kwh = nrg.calc_idle_kwh(idle_time_s)

        req_time_s = (request.dropoff_time - request.pickup_time).total_seconds()
        req_dist_mi = request.distance_miles
        req_energy_kwh = nrg.calc_trip_kwh(req_dist_mi, req_time_s, veh.WH_PER_MILE_LOOKUP)
        total_energy_use_kwh = idle_energy_kwh + disp_energy_kwh + req_energy_kwh
        hyp_energy_remaining = veh.energy_remaining - total_energy_use_kwh
        hyp_soc = hyp_energy_remaining / veh.BATTERY_CAPACITY

        calcs = {
            'idle_start_time': idle_start_time,
            'idle_end_time': idle_end_time,
            'idle_time_s': idle_time_s,
            'idle_energy_kwh': idle_energy_kwh,
            'dispatch_start_time': disp_start_time,
            'dispatch_end_time': disp_end_time,
            'dispatch_time_s': disp_time_s,
            'dispatch_energy_kwh': disp_energy_kwh,
            'dispatch_dist_miles': disp_dist_mi,
            'request_energy_kwh': req_energy_kwh,
        }

        # 0.1 Update Vehicles that should have been charging at a FuelStation
        if veh.soc < veh.ENV['LOWER_SOC_THRESH_STATION']:
            if cfg.DEBUG: print(f"ACTIVE: I am vehicle {veh.ID} and I need to charge")
            station, station_dist_mi = self._find_nearest_plug(veh, type='station')
            veh.refuel_at_station(station, station_dist_mi)
            self.stats['failure_active_time']+=1
            return False, None

        # 0.2 Update Vehicles that should have returned to VehicleBase
        if idle_time_min > veh.ENV['MAX_ALLOWABLE_IDLE_MINUTES']:
            if cfg.DEBUG: print(f"ACTIVE: I am vehicle {veh.ID} and I need to return to base")
            base, base_dist_mi = self._find_nearest_plug(veh, type='base')
            veh.return_to_base(base, base_dist_mi)
            self._active_fleet.remove(veh) #pop veh from active queue
            self._inactive_fleet.append(veh) #append veh to end of inactive queue
            return False, None

        # Check 1 - Max Dispatch Constraint Not Violated
        if disp_dist_mi > veh.ENV['MAX_DISPATCH_MILES']:
            if cfg.DEBUG: print(f"ACTIVE: I am vehicle {veh.ID} and I am too far away")
            self.stats['failure_active_max_dispatch']+=1
            return False, None

        # Check 2 - Time Constraint Not Violated
        if veh.avail_time + datetime.timedelta(seconds=disp_time_s) > request.pickup_time:
            if cfg.DEBUG:
                print(f"ACTIVE: I am vehicle {veh.ID} and I can't make it in time")
                print(f"Time to get there: {disp_time_s} seconds")
                print(f"avail time: {veh.avail_time}, request time: {request.pickup_time}")
            self.stats['failure_active_time']+=1
            return False, None

        # Check 3 - Battery Constraint Not Violated
        if hyp_soc < veh.ENV['MIN_ALLOWED_SOC']:
            if cfg.DEBUG: print(f"ACTIVE: I am vehicle {veh.ID} and I don't have enough power")
            self.stats['failure_active_battery']+=1
            return False, None

        # Check 4 - Max Occupancy Constraint Not Violated
        if request.passengers > veh.avail_seats:
            if cfg.DEBUG: print(f"ACTIVE: I am vehicle {veh.ID} and I don't have enough seats")
            self.stats['failure_active_occupancy']+=1
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
        disp_dist_mi = hlp.estimate_vmt_2D(veh.x,
                                        veh.y,
                                        request.pickup_x,
                                        request.pickup_y,
                                        scaling_factor = veh.ENV['RN_SCALING_FACTOR'])
        disp_time_s = (disp_dist_mi/veh.ENV['DISPATCH_MPH']) * 3600
        disp_end_time = request.pickup_time
        disp_start_time = disp_end_time - datetime.timedelta(seconds=disp_time_s)
        disp_energy_kwh = nrg.calc_trip_kwh(disp_dist_mi,
                                            disp_time_s,
                                            veh.WH_PER_MILE_LOOKUP)

        req_time_s = (request.dropoff_time - request.pickup_time).total_seconds()
        req_dist_mi = request.distance_miles
        req_energy_kwh = nrg.calc_trip_kwh(req_dist_mi,
                                           req_time_s,
                                           veh.WH_PER_MILE_LOOKUP)

        base_plug_power_kw = veh.base.PLUG_POWER_KW
        base_plug_type = veh.base.PLUG_TYPE
        base_refuel_start = veh.avail_time
        hyp_base_refuel_end = disp_start_time
        hyp_refuel_s = (hyp_base_refuel_end - base_refuel_start).total_seconds()

        if base_plug_type == 'AC':
            hyp_base_refuel_energy_kwh = chrg.calc_const_charge_kwh(hyp_refuel_s,
                                                                    base_plug_power_kw)
        elif base_plug_type == 'DC':
            soc_i = veh.soc
            hyp_base_refuel_energy_kwh = chrg.calc_dcfc_kwh(veh.CHARGE_TEMPLATE,
                                                            veh.BATTERY_CAPACITY,
                                                            veh.MAX_CHARGE_ACCEPTANCE_KW,
                                                            soc_i * 100,
                                                            hyp_refuel_s)

        hyp_battery_charge = veh.energy_remaining + hyp_base_refuel_energy_kwh

        if hyp_battery_charge >= veh.BATTERY_CAPACITY:
            reserve=True
            battery_charge = veh.BATTERY_CAPACITY
            base_refuel_energy_kwh = battery_charge - veh.energy_remaining
            soc_f = 1.0
            if veh.base.PLUG_TYPE == 'AC':
                base_refuel_s = chrg.calc_const_charge_secs(veh.energy_remaining,
                                                            veh.BATTERY_CAPACITY,
                                                            base_plug_power_kw,
                                                            soc_f)
            elif veh.base.PLUG_TYPE == 'DC':
                soc_i = veh.soc
                base_refuel_s = chrg.calc_dcfc_secs(veh.CHARGE_TEMPLATE,
                                                    veh.BATTERY_CAPACITY,
                                                    veh.MAX_CHARGE_ACCEPTANCE_KW,
                                                    soc_i * 100,
                                                    soc_f * 100)
            base_refuel_end = veh.avail_time + datetime.timedelta(seconds=base_refuel_s)
            base_refuel_start_soc = veh.energy_remaining / veh.BATTERY_CAPACITY
            base_refuel_end_soc = battery_charge / veh.BATTERY_CAPACITY
            base_reserve_start = base_refuel_end
            base_reserve_end = disp_start_time
        else:
            reserve=False
            #set actual values == hypothetical values calculated initially
            base_refuel_s = hyp_refuel_s
            base_refuel_end = hyp_base_refuel_end
            base_refuel_energy_kwh = hyp_base_refuel_energy_kwh

            battery_charge = veh.energy_remaining + base_refuel_energy_kwh
            base_refuel_start_soc = veh.soc
            base_refuel_end_soc = battery_charge / veh.BATTERY_CAPACITY
            base_reserve_start = None
            base_reserve_end = None


        hyp_energy_remaining = battery_charge - disp_energy_kwh - req_energy_kwh
        hyp_soc = hyp_energy_remaining / veh.BATTERY_CAPACITY

        calcs = {
            'base_refuel_start_soc': base_refuel_start_soc,
            'base_refuel_start_time': base_refuel_start,
            'base_refuel_end_soc': base_refuel_end_soc,
            'base_refuel_end_time': base_refuel_end,
            'base_refuel_s': base_refuel_s,
            'base_refuel_energy_kwh': base_refuel_energy_kwh,
            'base_reserve_start_time': base_reserve_start,
            'base_reserve_end_time': base_reserve_end,
            'dispatch_start_time': disp_start_time,
            'dispatch_end_time': disp_end_time,
            'dispatch_time_s': disp_time_s,
            'dispatch_energy_kwh': disp_energy_kwh,
            'dispatch_dist_miles': disp_dist_mi,
            'request_energy_kwh': req_energy_kwh,
            'reserve': reserve
        }

        # Check 1 - Time Constraint Not Violated
        if (veh.avail_time!=None) and \
        (veh.avail_time + datetime.timedelta(seconds=disp_time_s) > request.pickup_time):
            if cfg.DEBUG:
                print(f"INACTIVE: I am vehicle {veh.ID} and I can't make it in time")
                print(f"Time to get there: {disp_time_s} seconds")
                print(f"avail time: {veh.avail_time}, request time: {request.pickup_time}")

            self.stats['failure_inactive_time']+=1
            return False, None

        # Check 2 - Battery Constraint Not Violated
        if hyp_soc < veh.ENV['MIN_ALLOWED_SOC']:
            if cfg.DEBUG: print(f"INACTIVE: I am vehicle {veh.ID} and I don't have enough power")
            self.stats['failure_inactive_battery']+=1
            return False, None

        # Check 3 - Max Occupancy Constraint Not Violated
        if request.passengers > veh.avail_seats:
            if cfg.DEBUG: print(f"INACTIVE: I am vehicle {veh.ID} and I don't have enough seats")
            self.stats['failure_inactive_occupancy']+=1
            return False, None

        return True, calcs

    def _find_nearest_plug(self, vehicle, type='station'):
        """
        Function takes hive.vehicle.Vehicle object and returns the FuelStation
        nearest Vehicle with at least one available plug. The "type" argument
        accepts either 'station' or 'base', informing the search space.
        """
        #IDEA: Store stations in a geospatial index to eliminate exhaustive search. -NR
        INF = 1000000000

        if type == 'station':
            network = self._stations
        elif type == 'base':
            network = self._bases

        def recursive_search(search_space):
            if len(search_space) < 1:
                raise NotImplementedError("""No plugs are available on the
                    entire network.""")

            dist_to_nearest = INF
            for id, station in search_space.items():
                dist_mi = hlp.estimate_vmt_2D(vehicle.x,
                                               vehicle.y,
                                               station.X,
                                               station.Y,
                                               scaling_factor = vehicle.ENV['RN_SCALING_FACTOR'])
                if dist_mi < dist_to_nearest:
                    dist_to_nearest = dist_mi
                    nearest = station
            if nearest.avail_plugs < 1:
                search_space = {k:v for k,v in search_space.items() if k.ID != nearest.ID}
                nearest = recursive_search(search_space)

            return nearest, dist_to_nearest

        nearest, dist_to_nearest = recursive_search(network)

        return nearest, dist_to_nearest

    # def _find_nearest_plug(self, veh, type='station'):
    #     """
    #     Function takes hive.vehicle.Vehicle object and returns the FuelStation
    #     nearest Vehicle with at least one available plug. The "type" argument
    #     accepts either 'station' or 'base', informing the search space.
    #     """
    #     #IDEA: Store stations in a geospatial index to eliminate exhaustive search. -NR
    #     INF = 1000000000
    #
    #     assert type in ['station', 'base'], """"type" must be either 'station'
    #     or 'base'."""
    #
    #     if type == 'station':
    #         network = self._stations
    #     elif type == 'base':
    #         network = self._bases
    #
    #     i = 0
    #     num_stations = len(network)
    #     nearest = None
    #     while nearest == None:
    #         dist_to_nearest = INF
    #         for id in network.keys():
    #             station = network[id]
    #             dist_mi = hlp.estimate_vmt_2D(veh.x,
    #                                            veh.y,
    #                                            station.X,
    #                                            station.Y,
    #                                            scaling_factor = veh.ENV['RN_SCALING_FACTOR'])
    #             if dist_mi < dist_to_nearest:
    #                 dist_to_nearest = dist_mi
    #                 nearest = station
    #         if nearest.avail_plugs < 1:
    #             del network[nearest.ID]
    #             nearest == None
    #         i += 1
    #         if i >= num_stations:
    #             raise NotImplementedError("""No plugs are available on the
    #                 entire {} network.""".format(type))
    #
    #     return nearest, dist_to_nearest

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
            self._reset_failure_tracking()
            for veh in self._active_fleet: #check active fleet vehicles first
                viable, calcs = self._check_active_viability(veh, req)
                if viable:
                    veh.make_trip(req, calcs)
                    self._active_fleet.remove(veh) #pop veh from active queue
                    self._active_fleet.append(veh) #append veh to end of active queue
                    req_filled = True
                    break
            if not req_filled:
                for veh in self._inactive_fleet: #check inactive fleet vehicles second
                    viable, calcs = self._check_inactive_viability(veh, req)
                    if viable:
                        veh.make_trip(req, calcs)
                        # With full information of charge event, update logs/tracking
                        base = self._bases[veh.base.ID]
                        base.add_charge_event(veh,
                                                calcs['base_refuel_start_time'],
                                                calcs['base_refuel_end_time'],
                                                calcs['base_refuel_start_soc'],
                                                calcs['base_refuel_end_soc'],
                                                calcs['base_refuel_energy_kwh'])
                        self._inactive_fleet.remove(veh) #pop veh from inactive queue
                        self._active_fleet.append(veh) #append veh to end of active queue
                        base.avail_plugs += 1 # Freeing up plug for others to use
                        req_filled = True
                        break
            if not req_filled:
                if cfg.DEBUG: print('Dropped req.')
                write_log({
                    'pickup_time': req.pickup_time,
                    'dropoff_time': req.dropoff_time,
                    'distance_miles': req.distance_miles,
                    'pickup_lat': req.pickup_lat,
                    'pickup_lon': req.pickup_lon,
                    'dropoff_lat': req.dropoff_lat,
                    'dropoff_lon': req.dropoff_lon,
                    'passengers': req.passengers,
                    'failure_active_max_dispatch': self.stats['failure_active_max_dispatch'],
                    'failure_active_time': self.stats['failure_active_time'],
                    'failure_active_battery': self.stats['failure_active_battery'],
                    'failure_active_occupancy': self.stats['failure_active_occupancy'],
                    'failure_inactive_time': self.stats['failure_inactive_time'],
                    'failure_inactive_battery': self.stats['failure_inactive_battery'],
                    'failure_inactive_occupancy': self.stats['failure_inactive_occupancy']
                },
                self._LOG_COLUMNS,
                self._logfile)

    def get_fleet(self):
        """
        Function recombines internal _active_fleet and _inactive_fleet objects
        into a single list.
        """
        full_fleet = self._active_fleet + self._inactive_fleet

        return full_fleet
