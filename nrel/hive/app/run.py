from __future__ import annotations

import argparse
import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING, Iterable, Optional, Tuple, TypeVar, Union

import pkg_resources
import yaml
import random
import numpy

from nrel.hive.dispatcher.instruction_generator.instruction_generator import InstructionGenerator
from nrel.hive.initialization.initialize_simulation import InitFunction
from nrel.hive.initialization.load import load_simulation, load_config
from nrel.hive.runner.local_simulation_runner import LocalSimulationRunner

if TYPE_CHECKING:
    pass

parser = argparse.ArgumentParser(description="run hive")
parser.add_argument(
    "scenario_file",
    help='which scenario file to run (try "denver_downtown.yaml" or "manhattan.yaml")',
)
parser.add_argument(
    "--defaults",
    dest="defaults",
    action="store_true",
    help="prints the default hive configuration values",
)

log = logging.getLogger("hive")

T = TypeVar("T", bound=InstructionGenerator)


def run_sim(
    scenario_file: Union[Path, str],
    custom_instruction_generators: Optional[Tuple[T, ...]] = None,
    custom_init_functions: Optional[Iterable[InitFunction]] = None,
):
    """
    runs a single sim and writes outputs

    :param scenario_file: the scenario file to run
    :param custom_instruction_generators: a set of user defined instruction generators to override the defaults
    :param custom_init_functions: a set of user defined initialization functions to override the defaults

    :return: 0 for success
    """
    _welcome_to_hive()

    config = load_config(scenario_file)

    if config.sim.seed is not None:
        random.seed(config.sim.seed)
        numpy.random.seed(config.sim.seed)

    initial_payload = load_simulation(
        config,
        custom_instruction_generators=custom_instruction_generators,
        custom_init_functions=custom_init_functions,
    )

    log.info(
        f"running {initial_payload.e.config.sim.sim_name} for time {initial_payload.e.config.sim.start_time} "
        f"to {initial_payload.e.config.sim.end_time}:"
    )
    start = time.time()
    sim_result = LocalSimulationRunner.run(initial_payload)
    end = time.time()

    log.info(f"done! time elapsed: {round(end - start, 2)} seconds")

    sim_result.e.reporter.close(sim_result)

    if initial_payload.e.config.global_config.write_outputs:
        initial_payload.e.config.to_yaml()

    return 0


def run(
    custom_instruction_generators: Optional[Tuple[T, ...]] = None,
    custom_init_functions: Optional[Iterable[InitFunction]] = None,
) -> int:
    """
    entry point for a hive application run
    :return: 0 if success, 1 if error
    """
    # parse arguments
    try:
        args = parser.parse_args()
    except:
        parser.print_help()
        print_defaults()
        return 1

    # main application
    if args.defaults:
        print_defaults()

    return run_sim(args.scenario_file, custom_instruction_generators, custom_init_functions)


def _welcome_to_hive():
    welcome = """
##     ##  ####  ##     ##  #######
##     ##   ##   ##     ##  ##
#########   ##   ##     ##  ######
##     ##   ##    ##   ##   ##
##     ##  ####     ###     #######

                .' '.            __
       .        .   .           (__\_
        .         .         . -{{_(|8)
          ' .  . ' ' .  . '     (__/
    """

    log.info(welcome)


def print_defaults():
    print()
    defaults_file_str = pkg_resources.resource_filename(
        "nrel.hive.resources.defaults", "hive_config.yaml"
    )
    log.info(f"printing the default scenario configuration stored at {defaults_file_str}:\n")
    # start build using the Hive config defaults file
    defaults_file = Path(defaults_file_str)

    with defaults_file.open("r") as f:
        conf = yaml.safe_load(f)
        print(yaml.dump(conf))
    log.info("finished printing default scenario configuration")


if __name__ == "__main__":
    run()
