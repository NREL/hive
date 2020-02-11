import os
from datetime import datetime
import logging
from typing import Tuple

import yaml
from dispatcher.forecaster import BasicForecaster
from dispatcher.manager import BasicManager
from hive.config import HiveConfig
from hive.runner import LocalSimulationRunner
from hive.reporting import Reporter, DetailedReporter
from hive.runner import RunnerPayload
from hive.state import initialize_simulation, SimulationState
from hive.dispatcher import ManagedDispatcher
from pkg_resources import resource_filename
from state.update import ChargingPriceUpdate, UpdateRequests, CancelRequests, StepSimulation

log = logging.getLogger(__name__)


def load_local_simulation(scenario_file_path: str) -> Tuple[LocalSimulationRunner, Reporter, SimulationState]:
    """
    takes a scenario path and attempts to build all assets required to run a scenario
    :param scenario_file_path: the path to the scenario file we are using
    :return: the assets required to run a scenario
    :raises: Exception if the scenario_path is not found or if other scenario files are not found or fail to parse
    """
    with open(scenario_file_path, 'r') as f:
        config_builder = yaml.safe_load(f)

    config = HiveConfig.build(config_builder)
    if isinstance(config, Exception):
        log.error("attempted to load scenario config file but failed")
        raise config

    run_name = config.sim.sim_name + '_' + datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    sim_output_dir = os.path.join(config.io.working_directory, run_name)
    if not os.path.isdir(sim_output_dir):
        os.makedirs(sim_output_dir)

    log.info("initializing scenario")

    simulation_state, environment = initialize_simulation(config)

    requests_file = resource_filename("hive.resources.requests", config.io.requests_file)
    rate_structure_file = resource_filename("hive.resources.service_prices", config.io.rate_structure_file)
    charging_price_file = resource_filename("hive.resources.charging_prices", config.io.charging_price_file)

    runner = LocalSimulationRunner(env=environment)
    reporter = DetailedReporter(config.io, sim_output_dir)

    return runner, reporter, simulation_state
