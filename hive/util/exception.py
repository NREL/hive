class StateTransitionError(Exception):
    """
    calls out a breach in the simulation's physics observed when
    a state transition's invariants are not met.
    """

    def __init__(self, state_type, this_state_name, next_state_name):
        """

        :param state_type: the kind of state object that failed (i.e, "vehicle", "charger", "request")
        :param this_state_name: state at beginning of transition
        :param next_state_name: attempted new state
        """
        self.this_state = this_state_name
        self.next_state = next_state_name
        self.message = "Illegal {} state transition from {} to {}".format(
            state_type,
            this_state_name,
            next_state_name,
        )

    def __init__(self, msg):
        self.message = msg

    def __str__(self):
        return repr(self.message)


class StateOfChargeError(Exception):
    """
    state of charge must exist in the range [0, 1]
    """

    def __init__(self, soc):
        self.message = "Illegal state of charge value {}".format(soc)

    def __str__(self):
        return repr(self.message)


class RouteStepError(Exception):
    """
    errors related to stepping forward along a route
    """

    def __init__(self, msg):
        self.message = msg

    def __str__(self):
        return repr(self.message)


class SimulationStateError(Exception):
    """
    errors related to SimulationState operations
    """

    def __init__(self, msg):
        self.message = msg

    def __str__(self):
        return repr(self.message)


class EntityError(Exception):
    """
    errors related to methods on entities such as vehicles or stations.
    """

    def __init__(self, msg):
        self.message = msg

    def __str__(self):
        return repr(self.message)
