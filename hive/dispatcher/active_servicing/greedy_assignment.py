"""
Dispatcher Object for high-level decision making in HIVE. Includes functions for
vehicle dispatching, and station/base selection.
"""

import numpy as np

from hive import helpers as hlp
from hive import units
from hive.utils import generate_csv_row
from hive.dispatcher.active_servicing import AbstractServicing
from hive.vehiclestate import VehicleState


class GreedyAssignment(AbstractServicing):
    """
    Uses a greedy strategy to create agent plans

    Parameters
    ----------
    fleet: list
        list of all vehicles in the fleet.
    fleet_state: np.ndarray
        matrix that represents the state of the fleet. Used for quick numpy vectorized operations.
    stations: list
        list of all charging stations.
    bases: list
        list of all bases
    env_params: dict
        dictionary of all of the constant environment parameters shared across the simulation.
    clock: hive.utils.Clock
        simulation clock shared across the simulation to track simulation time steps.
    """

    def __init__(
                self,
                fleet,
                fleet_state,
                stations,
                bases,
                demand,
                env_params,
                route_engine,
                clock,
                log,
                ):
        super().__init__(
                fleet,
                fleet_state,
                stations,
                bases,
                demand,
                env_params,
                route_engine,
                clock,
                log,
        )

    def log(self):
        if not self.logger:
            return

        active_col = self._ENV['FLEET_STATE_IDX']['active']
        active_vehicles = self._fleet_state[:, active_col].sum()
        available_col = self._ENV['FLEET_STATE_IDX']['available']
        available_vehicles = self._fleet_state[:, available_col].sum()

        info = [
            ('sim_time', self._clock.now),
            ('time', self._clock.get_time()),
            ('active_vehicles', active_vehicles),
            ('active_target', self._active_fleet_target),
            ('available_vehicles', available_vehicles),
            ('dropped_requests', self._dropped_requests),
            ('total_requests', self._total_requests),
            ('wait_time_min', self._wait_time_min),
            ]

        self.logger.info(generate_csv_row(info, self.LOG_COLUMNS))

    def _get_n_best_vehicles(self, request, n):
        """
        Function takes a single request and returns the n best vehicles with respect
        to that request.

        Parameters
        ----------
        request: NamedTuple
            request named tuple to match n vehicles to.
        n: int
            how many vehicles to return.

        Returns
        -------
        best_vehs_ids: np.ndarray
            array of the best n vehicle ids in sorted order from best -> worst.

        """
        fleet_state = self._fleet_state
        point = np.array([request.pickup_lat, request.pickup_lon])
        lat_col = self._ENV['FLEET_STATE_IDX']['lat']
        lon_col = self._ENV['FLEET_STATE_IDX']['lon']
        dist = hlp.haversine_np(
                        fleet_state[:, lat_col].astype(np.float64),
                        fleet_state[:, lon_col].astype(np.float64),
                        point[0],
                        point[1],
                        )

        best_vehs_idx = np.argsort(dist)
        dist_mask = dist < self._ENV['MAX_DISPATCH_MILES']

        available_col = self._ENV['FLEET_STATE_IDX']['available']
        available_mask = (fleet_state[:,available_col] == 1)

        #TODO: Update this to include energy required to dispatch and get to
        #      nearest charger.
        soc_col = self._ENV['FLEET_STATE_IDX']['soc']
        KWH__MI_col = self._ENV['FLEET_STATE_IDX']['KWH__MI']
        BATTERY_CAPACITY_KWH_col = self._ENV['FLEET_STATE_IDX']['BATTERY_CAPACITY_KWH']
        min_soc_mask = (fleet_state[:, soc_col] \
            - ((dist + request.distance_miles) * fleet_state[:, KWH__MI_col]) \
            /fleet_state[:, BATTERY_CAPACITY_KWH_col] > self._ENV['MIN_ALLOWED_SOC'])

        avail_seats_col = self._ENV['FLEET_STATE_IDX']['avail_seats']
        avail_seats_mask = fleet_state[:, avail_seats_col] >= request.passengers

        mask = dist_mask & available_mask & min_soc_mask & avail_seats_mask
        best_vehs_ids = best_vehs_idx[mask[best_vehs_idx]][:n]
        return best_vehs_ids

    def _dispatch_vehicles(self, requests):
        """
        Function coordinates vehicle dispatch actions for a single timestep given
        one or more requests.

        Parameters
        ----------
        requests: list
            list of requests that occur in a single time step.
        """
        self._dropped_requests = 0
        self._total_requests = len(requests)
        self._wait_time_min = 0
        for request in requests.itertuples():
            best_vehicle = self._get_n_best_vehicles(request, n=1)
            if len(best_vehicle) < 1:
                self._dropped_requests += 1
            else:
                vehid = best_vehicle[0]
                veh = self._fleet[vehid]
                disp_route_summary = self._route_engine.route(
                                        veh.lat,
                                        veh.lon,
                                        request.pickup_lat,
                                        request.pickup_lon,
                                        vehicle_state=VehicleState.DISPATCH_TRIP)
                disp_route = disp_route_summary['route']
                self._wait_time_min += disp_route_summary['trip_time_s'] * units.SECONDS_TO_MINUTES

                if hasattr(request, 'route'):
                    trip_route = request.route
                else:
                    trip_route_summary = self._route_engine.route(
                                            request.pickup_lat,
                                            request.pickup_lon,
                                            request.dropoff_lat,
                                            request.dropoff_lon,
                                            vehicle_state=VehicleState.SERVING_TRIP,
                                            trip_dist_mi = request.distance_miles,
                                            trip_time_s = request.seconds,
                                            )
                    trip_route = trip_route_summary['route']

                del disp_route[-1]
                route = disp_route + trip_route

                veh.cmd_make_trip(
                        route = route,
                        passengers = request.passengers,
                        )


    def process_requests(self, requests):
        """
        process_requests is called for each simulation time step. Function takes
        a list of requests and coordinates vehicle actions for that step.

        Parameters
        ----------
        requests: list
            one or many requests to distribute to the fleet.
        """
        self._dispatch_vehicles(requests)
