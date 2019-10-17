from abc import ABC, abstractmethod


class AbstractRepositioning(ABC):
    """
    functions expected to be found on a Repositioning module
    """

    @abstractmethod
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

        super().__init__()

        self._fleet = fleet
        self._fleet_state = fleet_state
        self._route_engine = route_engine
        self._clock = clock
        self._stations = stations
        self._bases = bases

        self._ENV = env_params

    @abstractmethod
    def reposition_agents(self):
        """
        makes decisions related to agent repositioning at each time step
        """
        pass

    @abstractmethod
    def log(self):
        """
        Function stores the partial state of the object at each time step.
        :return:
        """
        pass
