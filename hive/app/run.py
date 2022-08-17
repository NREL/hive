from __future__ import annotations

import argparse
import logging
import os
import time
from pathlib import Path
from typing import TYPE_CHECKING

import pkg_resources
import yaml

from hive.dispatcher.instruction_generator.charging_fleet_manager import ChargingFleetManager
from hive.dispatcher.instruction_generator.dispatcher import Dispatcher
from hive.initialization.load import load_simulation
from hive.reporting import reporter_ops
from hive.runner.local_simulation_runner import LocalSimulationRunner
from hive.runner.runner_payload import RunnerPayload
from hive.state.simulation_state.update.update import Update
from hive.util import fs
from hive.util.fp import throw_on_failure

if TYPE_CHECKING:
    pass

parser = argparse.ArgumentParser(description="run hive")
parser.add_argument(
    'scenario_file',
    help='which scenario file to run (try "denver_downtown.yaml" or "manhattan.yaml")'
)
parser.add_argument(
    '--defaults',
    dest='defaults',
    action='store_true',
    help='prints the default hive configuration values'
)

log = logging.getLogger("hive")


def run_sim(scenario_file, position=0):
    """
    runs a single sim and writes outputs

    :param scenario_file: the scenario file to run
    :param position: the tqdm position

    :return: 0 for success
    """
    sim, env = load_simulation(scenario_file)

    # initialize logging
    logging.basicConfig(level=env.config.global_config.log_level, format='%(message)s')
    if env.config.global_config.log_run:
        run_log_path = os.path.join(env.config.scenario_output_directory, 'run.log')
        log_fh = logging.FileHandler(run_log_path)
        formatter = logging.Formatter("[%(levelname)s] - %(name)s - %(message)s")
        # log_fh.setLevel(env.config.global_config.log_level)
        log_fh.setFormatter(formatter)
        log.addHandler(log_fh)
        log.info(
            f"creating run log at {run_log_path} with log level {logging.getLevelName(log.getEffectiveLevel())}")

    if env.config.global_config.log_station_capacities:
        result = reporter_ops.log_station_capacities(sim, env)
        throw_on_failure(result)

    # build the set of instruction generators which compose the control system for this hive run
    # this ordering is important as the later managers will override any instructions from the previous
    # instruction generator for a specific vehicle id.
    instruction_generators = (
        ChargingFleetManager(env.config.dispatcher),
        Dispatcher(env.config.dispatcher),
    )

    update = Update.build(env.config, instruction_generators)
    initial_payload = RunnerPayload(sim, env, update)

    log.info(f"running {env.config.sim.sim_name} for time {initial_payload.e.config.sim.start_time} "
             f"to {initial_payload.e.config.sim.end_time}:")
    start = time.time()
    sim_result = LocalSimulationRunner.run(initial_payload, position)
    end = time.time()

    log.info(f'done! time elapsed: {round(end - start, 2)} seconds')

    env.reporter.close(sim_result)

    if env.config.global_config.write_outputs:
        env.config.to_yaml()

    return 0


def run() -> int:
    """
    entry point for a hive application run
    :return: 0 if success, 1 if error
    """
    
    _welcome_to_hive()

    # parse arguments
    try:
        args = parser.parse_args()
    except:
        parser.print_help()
        print_defaults()
        return 1

    # main application
    try:
        if args.defaults:
            print_defaults()

        # create the configuration and load the simulation
        try:
            scenario_file = fs.find_scenario(args.scenario_file)
        except FileNotFoundError as fe:
            log.error(f"{repr(fe)}; please specify a path to a hive scenario file like denver_demo.yaml")
            return 1


        run_sim(scenario_file)

        return 0

    except Exception as e:
        # perhaps in the future, a more robust handling here
        raise e


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
    defaults_file_str = pkg_resources.resource_filename("hive.resources.defaults", "hive_config.yaml")
    log.info(f"printing the default scenario configuration stored at {defaults_file_str}:\n")
    # start build using the Hive config defaults file
    defaults_file = Path(defaults_file_str)

    with defaults_file.open('r') as f:
        conf = yaml.safe_load(f)
        print(yaml.dump(conf))
    log.info("finished printing default scenario configuration")


if __name__ == "__main__":
    run()
