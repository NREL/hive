from abc import ABC, abstractmethod


class AbstractInactiveMgmt(ABC):
    """
    functions expected to be found on a Repositioning module
    """

    @abstractmethod
    def __init__(
            self,
            fleet,
            fleet_state,
            env_params,
            clock,
        ):

        super().__init__()

        self._fleet = fleet
        self._fleet_state = fleet_state
        self._clock = clock

        self._ENV = env_params

    @abstractmethod
    def manage_inactive_charging(self):
        """
        makes decisions related to inactive agents at each time step
        """
        pass

    @abstractmethod
    def activate_vehicles(self):
        """
        makes decisions related to inactive agents at each time step
        """
        pass

    @abstractmethod
    def log(self):
        """
        Function stores the partial state of the object at each time step.
        :return:
        """
        pass
