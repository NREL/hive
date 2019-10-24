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

        active_col = self._ENV['FLEET_STATE_IDX']['active']
        active_vehicles = self._fleet_state[:, active_col].sum()
        #
        ## Alternate method using a random number and current active vehicle count
        # active_n = active_vehicles + random.randint(-5,5)
        #
        # if now == 0:
        #     active_n = int(len(self._fleet) / 2)

        return active_n
