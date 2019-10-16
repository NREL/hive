class StateTransitionError(Exception):
    """Raised when an operation attempts a state transition that's not
    allowed.

    Attributes:
        state_type -- the kind of state object that failed (i.e, "vehicle", "charger", "request")
        this_state -- state at beginning of transition
        next_state -- attempted new state
    """

    def __init__(self, state_type, this_state_name, next_state_name):
        self.this_state = this_state_name
        self.next_state = next_state_name
        self.message = "Illegal {} state transition from {} to {}".format(
            state_type,
            this_state_name,
            next_state_name,
        )
