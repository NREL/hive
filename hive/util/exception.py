import functools as ft
from typing import Tuple, Dict


def report_error(error: Exception) -> Dict:
    """
    helper to enforce standardization of observed errors reported during simulation run

    :param error: the error that occurred during simulation
    :return: packaged as a report
    """
    data = {
        'report_type': 'error',
        'message': error.args
    }
    return data


class TimeParseError(Exception):
    """
    raised when time parsing fails
    """

    def __init__(self, msg):
        self.message = msg

    def __str__(self):
        return repr(self.message)


class StateTransitionError(Exception):
    """
    calls out a breach in the simulation's physics observed when
    a state transition's invariants are not met.
    """

    def __init__(self, state_type, this_state_name, next_state_name):
        """


        :param state_type: the kind of state object that failed (i.e, "vehicle", "charger_id", "request")
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


class UnitError(Exception):
    """
    errors related to units
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


class H3Error(Exception):
    """
    errors related to H3 operations
    """

    def __init__(self, msg):
        self.message = msg

    def __str__(self):
        return repr(self.message)


class CombinedException(Exception):
    """
    a bundle of errors which can be raised as a single Exception
    """

    def __init__(self, errors: Tuple[Exception, ...]):
        self.errors = errors

    def __str__(self):
        combined = ft.reduce(
            lambda acc, err: acc + f"{err.message}\n",
            self.errors,
            ""
        )
        return repr(combined)


class InstructionError(Exception):
    """
    reports that an instruction was erroneous
    """

    def __init__(self, msg):
        self.message = msg

    def __str__(self):
        return repr(self.message)
