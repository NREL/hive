import logging
import os
from typing import Tuple

import yaml

from hive.config import HiveConfig
from hive.runner.environment import Environment
from hive.state.simulation_state.initialize_simulation import initialize_simulation
from hive.state.simulation_state.simulation_state import SimulationState

run_log = logging.getLogger(__name__)


def load_simulation(scenario_file_path: str) -> Tuple[SimulationState, Environment]:
    """
    takes a scenario path and attempts to build all assets required to run a scenario
    :param scenario_file_path: the path to the scenario file we are using
    :return: the assets required to run a scenario
    :raises: Exception if the scenario_path is not found or if other scenario files are not found or fail to parse
    """
    with open(scenario_file_path, 'r') as f:
        config_builder = yaml.safe_load(f)

    try:
        config = HiveConfig.build(config_builder)
    except Exception as e:
        run_log.exception("attempted to load scenario config file but failed")
        raise e

    attempts = 0
    while attempts < 20:
        try:
            os.makedirs(config.output_directory)
            break
        except FileExistsError:
            config = config.refresh_output_directory()
            attempts += 1

    if attempts >= 20:
        e = IOError(f"Attempted to write log directory {config.output_directory} but failed after 20 attempts")
        run_log.exception(e)
        raise e

    simulation_state, environment = initialize_simulation(config)

    return simulation_state, environment
