import logging
import os
from pathlib import Path
from typing import Tuple

import yaml

from hive.config import HiveConfig
from hive.reporting.handler.eventful_handler import EventfulHandler
from hive.reporting.handler.instruction_handler import InstructionHandler
from hive.reporting.handler.stateful_handler import StatefulHandler
from hive.reporting.handler.stats_handler import StatsHandler
from hive.reporting.handler.time_step_stats_handler import TimeStepStatsHandler
from hive.reporting.reporter import Reporter
from hive.runner.environment import Environment
from hive.initialization.initialize_simulation import initialize_simulation
from hive.state.simulation_state.simulation_state import SimulationState

run_log = logging.getLogger(__name__)


def load_simulation(scenario_file_path: Path) -> Tuple[SimulationState, Environment]:
    """
    takes a scenario path and attempts to build all assets required to run a scenario

    :param scenario_file_path: the path to the scenario file we are using

    :return: the assets required to run a scenario
    :raises: Exception if the scenario_path is not found or if other scenario files are not found or fail to parse
    """
    with scenario_file_path.open('r') as f:
        config_builder = yaml.safe_load(f)

    try:
        config = HiveConfig.build(scenario_file_path, config_builder)
    except Exception as e:
        run_log.exception("attempted to load scenario config file but failed")
        raise e

    if config.global_config.write_outputs:
        config.scenario_output_directory.mkdir()

    simulation_state, environment = initialize_simulation(config)

    # configure reporting
    reporter = Reporter()
    if config.global_config.log_events:
        reporter.add_handler(EventfulHandler(config.global_config, config.scenario_output_directory))
    if config.global_config.log_states:
        reporter.add_handler(StatefulHandler(config.global_config, config.scenario_output_directory))
    if config.global_config.log_instructions:
        reporter.add_handler(InstructionHandler(config.global_config, config.scenario_output_directory))
    if config.global_config.log_stats:
        reporter.add_handler(StatsHandler())
    if config.global_config.log_time_step_stats or config.global_config.log_fleet_time_step_stats:
        reporter.add_handler(TimeStepStatsHandler(config, config.scenario_output_directory, environment.fleet_ids))

    environment_w_reporter = environment.set_reporter(reporter)

    return simulation_state, environment_w_reporter
