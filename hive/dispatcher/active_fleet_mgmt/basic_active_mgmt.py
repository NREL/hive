from hive.dispatcher.active_fleet_mgmt import AbstractRepositioning
from hive.vehiclestate import VehicleState

import hive.helpers as hlp

import numpy as np

class BasicActiveMgmt(AbstractRepositioning):
    """
    Simple active fleet management that lets vehicles time out.
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
                )
    def _find_closest_plug(self, vehicle, type='station'):
        """
        Function takes hive.vehicle.Vehicle object and returns the FuelStation
        nearest Vehicle with at least one available plug. The "type" argument
        accepts either 'station' or 'base', informing the search space.

        Parameters
        ----------
        vehicle: hive.vehicle.Vehicle
            vehicle to which the closest plug is relative to.
        type: str
            string to indicate which type of plug is being searched for.

        Returns
        -------
        nearest: hive.stations.FuelStation
            the station or bases that is the closest to the vehicle
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
            for station in search_space:
                dist_mi = hlp.estimate_vmt_latlon(vehicle.lat,
                                               vehicle.lon,
                                               station.LAT,
                                               station.LON,
                                               scaling_factor = vehicle.ENV['RN_SCALING_FACTOR'])
                if dist_mi < dist_to_nearest:
                    dist_to_nearest = dist_mi
                    nearest = station
            if nearest.avail_plugs < 1:
                search_space = [s for s in search_space if s.ID != nearest.ID]
                nearest = recursive_search(search_space)

            return nearest

        nearest = recursive_search(network)

        return nearest


    def _check_idle_vehicles(self):
        """
        Function checks for any vehicles that have been idling for longer than
        MAX_ALLOWABLE_IDLE_MINUTES and commands those vehicles to return to their
        respective base.
        """
        idle_min_col = self._ENV['FLEET_STATE_IDX']['idle_min']
        idle_mask = self._fleet_state[:, idle_min_col] >= self._ENV['MAX_ALLOWABLE_IDLE_MINUTES']
        veh_ids = np.argwhere(idle_mask)

        for veh_id in veh_ids:
            vehicle = self._fleet[veh_id[0]]
            base = self._find_closest_plug(vehicle, type='base')
            route_summary = self._route_engine.route(vehicle.lat, vehicle.lon,
                                                     base.LAT, base.LON,
                                                     VehicleState.DISPATCH_BASE)
            route = route_summary['route']
            vehicle.cmd_return_to_base(base, route)

    def reposition_agents(self):
        """
        """
        self._check_idle_vehicles()


    def log(self):
        """
        the best algorithms do no logging
        """
        pass
