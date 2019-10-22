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

    def calc_active_fleet_n(self):
        active_n = 0
        now = self._clock.now

        if now < len(self._demand) - 15:
            active_n = sum(self._demand[now:now+15]) + 20

        return active_n
