import random
import logging
import geopandas as gpd
from shapely.geometry import Point
import numpy as np

from hive.dispatcher.active_fleet_mgmt import BasicActiveMgmt
from hive.vehiclestate import VehicleState


class RandomRepositioning(BasicActiveMgmt):

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
            seed=0,
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

        self.random = random
        self.random.seed(seed)

        # invariant: should be a single polygon in the provided operating area file
        operating_area = gpd.read_file(env_params['operating_area_file_path'])
        self.bounding_box = operating_area.geometry[0]
        self.minx = float(operating_area.bounds['minx'])
        self.miny = float(operating_area.bounds['miny'])
        self.maxx = float(operating_area.bounds['maxx'])
        self.maxy = float(operating_area.bounds['maxy'])

        # sending debugger data to the run log for lack of a better destination
        self._log = logging.getLogger("run_log")

        # we haven't set up HIVE for repositioning logging
        # write repositioning log header
        # if log:
        #     header = self.LOG_COLUMNS[0]
        #     for column in self.LOG_COLUMNS[1:]:
        #         header = header + "," + column
        #     self.logger.info(header)

        self.agents_repositioned = 0
        self.random_locations_sampled = 0

    def reposition_agents(self):
        """
        randomly repositions Idle agents within the bounds of the simulation
        """
        fleet_state = self._fleet_state

        veh_ste_col = self._ENV['FLEET_STATE_IDX']['vehicle_state']

        agents_repositioned = 0
        random_locations_sampled = 0

        idle_veh_mask = (fleet_state[:, veh_ste_col] == VehicleState.IDLE.value)
        reposition_vehicles = np.argwhere(idle_veh_mask)

        # get all inactive agents
        for veh_id in reposition_vehicles:

            vehicle = self._fleet[veh_id[0]]
            # generate random points from min/max x/y values until a pair
            # falls within the bounding polygon (operating area) of the scenario

            rand_lon_pos = self.random.uniform(self.minx, self.maxx)
            rand_lat_pos = self.random.uniform(self.miny, self.maxy)
            random_locations_sampled = random_locations_sampled + 1
            while not self.bounding_box.contains(Point(rand_lon_pos, rand_lat_pos)):
                rand_lon_pos = self.random.uniform(self.minx, self.maxx)
                rand_lat_pos = self.random.uniform(self.miny, self.maxy)
                random_locations_sampled = random_locations_sampled + 1

            # route vehicle from current position to the randomly generated point
            route = self._route_engine.route(vehicle.lat, vehicle.lon,
                                            rand_lat_pos, rand_lon_pos,
                                            VehicleState.REPOSITIONING)
            vehicle.cmd_reposition(route['route'])
            agents_repositioned += 1

        self.agents_repositioned = self.agents_repositioned + agents_repositioned
        self.random_locations_sampled = self.random_locations_sampled + random_locations_sampled

        if self._log.isEnabledFor(logging.DEBUG):
            self._log.debug(
                "Random Repositioning finished at time step {} for {} agents".format(self._clock.get_time(),
                                                                                     agents_repositioned))

    def deactivate_vehicles(self, active_fleet_target):
        """
        does nothing!
        """
        pass

    def log(self):
        if self._log.isEnabledFor(logging.DEBUG):
            avg_samples = float(self.random_locations_sampled) / float(self.agents_repositioned)
            msg = "Random Repositioning avg location samples: {0:.2f}".format(avg_samples)
            self._log.debug(msg)
        # no real logging implemented yet for Repositioning modules
        pass
