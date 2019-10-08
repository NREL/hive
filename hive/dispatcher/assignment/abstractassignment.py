from abc import ABC, abstractmethod


class AbstractAssignment(ABC):
    """
    functions expected to be found on a Dispatcher
    """
    LOG_COLUMNS = [
        'sim_time',
        'time',
        'active_vehicles',
        'dropped_requests',
        'total_requests',
        'wait_time_min',
        ]

    def __init__(self):
        super().__init__()

    @abstractmethod
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
        log,
    ):
        """
        sets dispatcher up with relevant data for this simulation

        Parameters
        ----------
        fleet: list
            list of all vehicles in the fleet.
        fleet_state: np.ndarray
            matrix that represents the state of the fleet. Used for quick numpy vectorized operations.
        stations: list
            list of all charging stations.
        bases: list
            list of all bases
        demand
            demand
        env_params: dict
            dictionary of all of the constant environment parameters shared across the simulation.
        route_engine
            provides routing algorithm
        clock: hive.utils.Clock
            simulation clock shared across the simulation to track simulation time steps.
        """
        pass

    @abstractmethod
    def process_requests(self, requests):
        """
        process_requests is called for each simulation time step. Function takes
        a list of requests and coordinates vehicle actions for that step.

        Parameters
        ----------
        requests: list
            one or many requests to distribute to the fleet.
        """
        pass

    @abstractmethod
    def log(self):
        """
        Function stores the partial state of the object at each time step.
        :return:
        """
