from abc import ABC, abstractmethod


class AbstractRepositioning(ABC):
    """
    functions expected to be found on a Repositioning module
    """

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
        sets repositioning up with relevant data for this simulation

        Parameters
        ----------
        fleet: list
            list of all vehicles in the fleet.
        fleet_state: np.ndarray
            matrix that represents the state of the fleet. Used for quick numpy vectorized operations.
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
