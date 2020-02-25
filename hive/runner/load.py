import logging
import os
from datetime import datetime
from typing import Tuple

import yaml
from hive.runner import Environment
from hive.state import SimulationState
from hive.config import HiveConfig
from hive.state import initialize_simulation

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

    config = HiveConfig.build(config_builder)
    if isinstance(config, Exception):
        run_log.error("attempted to load scenario config file but failed")
        raise config

    run_name = config.sim.sim_name + '_' + datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    sim_output_dir = os.path.join(config.io.working_directory, run_name)
    if not os.path.isdir(sim_output_dir):
        os.makedirs(sim_output_dir)

    simulation_state, environment = initialize_simulation(config, sim_output_dir)

    return simulation_state, environment
