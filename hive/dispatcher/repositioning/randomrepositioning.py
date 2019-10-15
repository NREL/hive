import random
import logging

from hive.dispatcher.repositioning.abstractrepositioning import AbstractRepositioning


class RandomRepositioning(AbstractRepositioning):

    def __init__(self, seed=0):
        self.random = random
        self.random.seed(seed)
        self._log = None
        self.fleet = None
        self.fleet_state = None
        self.route_engine = None
        self.minx = None
        self.miny = None
        self.maxx = None
        self.maxy = None

    def spin_up(self, fleet, fleet_state, stations, bases, demand, env_params, route_engine, clock, log):
        self.fleet = fleet
        self.fleet_state = fleet_state
        self.route_engine = route_engine
        self.minx = env_params['BOUNDARY_MINX']
        self.miny = env_params['BOUNDARY_MINY']
        self.maxx = env_params['BOUNDARY_MAXX']
        self.maxy = env_params['BOUNDARY_MAXY']
        self._log = log

        # write repositioning log header
        # if log:
        #     header = self.LOG_COLUMNS[0]
        #     for column in self.LOG_COLUMNS[1:]:
        #         header = header + "," + column
        #     self.logger.info(header)

    def reposition_agents(self):
        """
        randomly repositions the agents within the bounds of the simulation
        """

        agents_repositioned = 0

        reposition_vehicles = list(filter(lambda veh: veh.activity == "Idle", self.fleet))

        # get all inactive agents
        for vehicle in reposition_vehicles:

            # TODO: repeat while x,y are not within polygon (requires polygon from config)

            rand_lon_pos = self.random.uniform(self.minx, self.maxx)
            rand_lat_pos = self.random.uniform(self.miny, self.maxy)
            route = self.route_engine.route(vehicle.lat, vehicle.lon, rand_lat_pos, rand_lon_pos, "Reposition")
            vehicle.cmd_reposition(route['route'])
            agents_repositioned += 1

        # self._log.info("repositioned {} agents".format(agents_repositioned))

    def log(self):
        pass
