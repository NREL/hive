import logging
import os
from pathlib import Path
from typing import Tuple

import yaml

from nrel.hive.config import HiveConfig
from nrel.hive.runner.environment import Environment
from nrel.hive.initialization.initialize_simulation import (
    default_init_functions,
    osm_init_function,
    initialize,
)
from nrel.hive.state.simulation_state.simulation_state import SimulationState

run_log = logging.getLogger(__name__)


def load_simulation(
    scenario_file_path: Path,
) -> Tuple[SimulationState, Environment]:
    """
    takes a scenario path and attempts to build all assets required to run a scenario

    :param scenario_file_path: the path to the scenario file we are using

    :return: the assets required to run a scenario
    :raises: Exception if the scenario_path is not found or if other scenario files are not found or fail to parse
    """
    with scenario_file_path.open("r") as f:
        config_builder = yaml.safe_load(f)

    config_or_error = HiveConfig.build(scenario_file_path, config_builder)
    if isinstance(config_or_error, Exception):
        run_log.exception("attempted to load scenario config file but failed")
        raise config_or_error
    else:
        config: HiveConfig = config_or_error

    if config.global_config.write_outputs:
        config.scenario_output_directory.mkdir()

    if config.network.network_type == "euclidean":
        init_functions = default_init_functions()
    elif config.network.network_type == "osm_network":
        init_functions = [osm_init_function]
        init_functions.extend(default_init_functions())

    return initialize(config, init_functions)
