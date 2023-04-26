import logging
import os
from pathlib import Path
from typing import Iterable, Optional, Tuple, TypeVar, Union

import yaml

from nrel.hive.config import HiveConfig
from nrel.hive.dispatcher.instruction_generator.charging_fleet_manager import ChargingFleetManager
from nrel.hive.dispatcher.instruction_generator.dispatcher import Dispatcher
from nrel.hive.dispatcher.instruction_generator.instruction_function import (
    instruction_generator_from_function,
    InstructionFunction,
)
from nrel.hive.dispatcher.instruction_generator.instruction_generator import (
    InstructionGenerator,
)
from nrel.hive.initialization.initialize_simulation import (
    default_init_functions,
    osm_init_function,
    initialize,
    InitFunction,
)
from nrel.hive.reporting import reporter_ops
from nrel.hive.runner.runner_payload import RunnerPayload
from nrel.hive.state.simulation_state.update.update import Update
from nrel.hive.util import fs
from nrel.hive.util.fp import throw_on_failure

log = logging.getLogger(__name__)

T = TypeVar("T", bound=Union[InstructionGenerator, InstructionFunction])


def load_config(scenario_file: Union[Path, str], output_suffix: Optional[str] = None) -> HiveConfig:
    try:
        scenario_file_path = fs.find_scenario(str(scenario_file))
    except FileNotFoundError as fe:
        raise FileNotFoundError(
            f"{repr(fe)}; please specify a path to a hive scenario file like denver_demo.yaml"
        )
    with scenario_file_path.open("r") as f:
        config_builder = yaml.safe_load(f)

    config_or_error = HiveConfig.build(scenario_file_path, config_builder, output_suffix)
    if isinstance(config_or_error, Exception):
        log.exception("attempted to load scenario config file but failed")
        raise config_or_error
    else:
        return config_or_error


def load_simulation(
    config: HiveConfig,
    custom_instruction_generators: Optional[Tuple[T, ...]] = None,
    custom_init_functions: Optional[Iterable[InitFunction]] = None,
) -> RunnerPayload:
    """
    takes a hive config and attempts to build all assets required to run a scenario

    :param config: the hive config
    :param custom_instruction_generators: a set of user defined instruction generators to override the defaults
    :param custom_init_functions: a set of user defined initialization functions to override the defaults

    :return: the assets required to run a scenario
    :raises: Exception if the scenario_path is not found or if other scenario files are not found or fail to parse
    """
    if config.global_config.write_outputs:
        config.scenario_output_directory.mkdir()

    if config.global_config.log_run:
        run_log_path = os.path.join(config.scenario_output_directory, "run.log")
        log_fh = logging.FileHandler(run_log_path)
        formatter = logging.Formatter("[%(levelname)s] - %(name)s - %(message)s")
        log_fh.setFormatter(formatter)
        log.addHandler(log_fh)
        log.info(
            f"creating run log at {run_log_path} with log level {logging.getLevelName(log.getEffectiveLevel())}"
        )

    if custom_init_functions is not None:
        # prefer the custom init functions
        init_functions = custom_init_functions
    elif config.network.network_type == "osm_network":
        init_functions = [osm_init_function]
        init_functions.extend(default_init_functions())
    else:
        # just use defaults
        init_functions = default_init_functions()

    sim, env = initialize(config, init_functions)

    if config.global_config.log_station_capacities:
        result = reporter_ops.log_station_capacities(sim, env)
        throw_on_failure(result)

    if custom_instruction_generators is None:
        instruction_generators = (
            Dispatcher(env.config.dispatcher),
            ChargingFleetManager(env.config.dispatcher),
        )
        update = Update.build(env.config, instruction_generators)
    else:
        # map all instruction functions to generators
        mapped_instruction_generators = tuple(
            map(
                lambda ig_or_if: instruction_generator_from_function(ig_or_if),
                custom_instruction_generators,
            )
        )
        update = Update.build(env.config, mapped_instruction_generators)

    return RunnerPayload(sim, env, update)
