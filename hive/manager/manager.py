import random

class Manager:
    def __init__(
            self,
            fleet,
            fleet_state,
            demand,
            env_params,
            clock,
        ):
        """
        """
        self._fleet = fleet
        self._fleet_state = fleet_state
        self._demand = demand

        self._clock = clock

        self._ENV = env_params

    def calc_fleet_differential(self):
        neg = int(random.random() * 2)

        diff = int(random.random() * 10) * (-1 * neg)
        return diff
