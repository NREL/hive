from hive.dispatcher.repositioning import AbstractRepositioning


class DoNothingRepositioning(AbstractRepositioning):
    """
    the laziest replanner, assumes that everything's gonna be great.
    """

    # reporting.generate_logs expects an attribute "history" which is indexed.
    # it inspects the first row and grabs the keys from that row to create
    # the header. this is the minimal placeholder to spoof that function.
    history = [{}]

    def spin_up(
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
        """
        mandatory constructor, but, nothing is stored since nothing happens
        """
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