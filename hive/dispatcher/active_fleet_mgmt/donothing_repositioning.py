from hive.dispatcher.active_fleet_mgmt import AbstractRepositioning


class DoNothingRepositioning(AbstractRepositioning):
    """
    the laziest replanner, assumes that everything's gonna be great.
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
        pass

    def reposition_agents(self):
        """
        does nothing!
        """
        pass

    def log(self):
        """
        the best algorithms do no logging
        """
        pass
