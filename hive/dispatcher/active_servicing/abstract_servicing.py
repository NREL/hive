from abc import ABC, abstractmethod


class AbstractServicing(ABC):
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
            log,
        ):

        super().__init__()
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
        self.ID = 0

        self._fleet = fleet
        self._fleet_state = fleet_state
        for veh in self._fleet:
            veh.fleet_state = fleet_state

        self._demand = demand

        self._clock = clock

        self._stations = stations
        self._bases = bases

        self._route_engine = route_engine

        self._dropped_requests = 0
        self._total_requests = 0
        self._wait_time_min = 0

        self._ENV = env_params

        self.logger = log

        # write dispatcher log header
        if log:
            header = self.LOG_COLUMNS[0]
            for column in self.LOG_COLUMNS[1:]:
                header = header + "," + column
            self.logger.info(header)

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

    def log(self):
        """
        Function stores the partial state of the object at each time step.
        :return:
        """
        if not self.logger:
            return

        active_col = self._ENV['FLEET_STATE_IDX']['active']
        active_vehicles = self._fleet_state[:, active_col].sum()

        info = [
            ('sim_time', self._clock.now),
            ('time', self._clock.get_time()),
            ('active_vehicles', active_vehicles),
            ('dropped_requests', self._dropped_requests),
            ('total_requests', self._total_requests),
            ('wait_time_min', self._wait_time_min),
            ]

        self.logger.info(generate_csv_row(info, self.LOG_COLUMNS))

    def _get_fleet_state_col(self, param):
        col = self._ENV['FLEET_STATE_IDX'][param]
        return self._fleet_state[:, col]
