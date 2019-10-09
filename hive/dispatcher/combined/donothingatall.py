from hive.dispatcher.combined.abstractcombined import AbstractCombined


class DoNothingAtAll(AbstractCombined):
    """
    just used to test the combined dispatch algorithm loader
    """

    # reporting.generate_logs expects an attribute "history" which is indexed.
    # it inspects the first row and grabs the keys from that row to create
    # the header. this is the minimal placeholder to spoof that function.
    history = [{}]

    def spin_up(self, fleet, fleet_state, stations, bases, demand, env_params, route_engine, clock, log):
        pass

    def process_requests(self, requests):
        pass

    def log(self):
        pass

    def reposition_agents(self):
        pass
