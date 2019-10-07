import random

from hive.dispatcher.repositioning.abstractrepositioning import AbstractRepositioning


class RandomRepositioning(AbstractRepositioning):

    def __init__(self, seed=0):
        self.random = random.seed(seed)

    def spin_up(self, fleet, fleet_state, stations, bases, demand, env_params, route_engine, clock):
        pass

    def reposition_agents(self):
        pass

    def log(self):
        pass
