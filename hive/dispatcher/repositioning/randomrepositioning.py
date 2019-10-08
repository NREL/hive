import random
import logging

from hive.dispatcher.repositioning.abstractrepositioning import AbstractRepositioning


class RandomRepositioning(AbstractRepositioning):

    def __init__(self, seed=0):
        self.random = random
        self.random.seed(seed)
        self._log = logging.getLogger(__name__)
        self.fleet = None
        self.fleet_state = None
        self.route_engine = None
        self.minx = None
        self.miny = None
        self.maxx = None
        self.maxy = None

    def spin_up(self, fleet, fleet_state, stations, bases, demand, env_params, route_engine, clock):
        self.fleet = fleet
        self.fleet_state = fleet_state
        self.route_engine = route_engine
        self.minx = env_params['BOUNDARY_MINX']
        self.miny = env_params['BOUNDARY_MINY']
        self.maxx = env_params['BOUNDARY_MAXX']
        self.maxy = env_params['BOUNDARY_MAXY']

    def reposition_agents(self):
        """
        randomly repositions the agents within the bounds of the simulation
        """

        agents_repositioned = 0

        reposition_vehicles = list(filter(lambda veh: veh.activity == "Idle", self.fleet))

        # get all inactive agents
        for vehicle in reposition_vehicles:
            rand_x_pos = self.random.uniform(self.minx, self.maxx)
            rand_y_pos = self.random.uniform(self.miny, self.maxy)
            route = self.route_engine.route(vehicle.x, vehicle.y, rand_x_pos, rand_y_pos, "Reposition")
            vehicle.cmd_reposition(route['route'])
            agents_repositioned += 1

        self._log.debug("repositioned {} agents".format(agents_repositioned))

    def log(self):
        pass
