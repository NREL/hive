from hive.repositioning.Repositioning import AbstractRepositioning


class DoNothingRepositioning(AbstractRepositioning):
    """
    the laziest replanner, assumes that everything's gonna be great.
    """

    def spin_up(
            self,
            fleet,
            fleet_state,
            demand,
            env_params,
            route_engine,
            clock,
    ):
        """
        mandatory constructor, but, nothing is stored since nothing happens
        """
        pass

    def reposition_agents(self):
        """
        does nothing!
        """
        pass
