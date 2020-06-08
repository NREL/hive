from __future__ import annotations

import argparse
import functools as ft
import logging
import os
import time
from pathlib import Path
from typing import NamedTuple, TYPE_CHECKING

import pkg_resources
import yaml

from hive.dispatcher.forecaster.basic_forecaster import BasicForecaster
from hive.dispatcher.instruction_generator.base_fleet_manager import BaseFleetManager
from hive.dispatcher.instruction_generator.charging_fleet_manager import ChargingFleetManager
from hive.dispatcher.instruction_generator.dispatcher import Dispatcher
from hive.dispatcher.instruction_generator.position_fleet_manager import PositionFleetManager
from hive.model.vehicle import Vehicle
from hive.runner.load import load_simulation
from hive.runner.local_simulation_runner import LocalSimulationRunner
from hive.runner.runner_payload import RunnerPayload
from hive.state.simulation_state.simulation_state import SimulationState
from hive.state.simulation_state.update import Update
from hive.util import fs

if TYPE_CHECKING:
    from hive.runner.environment import Environment

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
            sim, env = load_simulation(scenario_file)
        except FileNotFoundError as fe:
            log.error(fe)
            return 1

        # initialize logging
        logging.basicConfig(level=env.config.global_config.log_level, format='%(message)s')
        if env.config.global_config.log_run:
            run_log_path = os.path.join(env.config.scenario_output_directory, 'run.log')
            log_fh = logging.FileHandler(run_log_path)
            formatter = logging.Formatter("[%(levelname)s] - %(name)s - %(message)s")
            # log_fh.setLevel(env.config.global_config.log_level)
            log_fh.setFormatter(formatter)
            log.addHandler(log_fh)
            log.info(f"creating run log at {run_log_path} with log level {logging.getLevelName(log.getEffectiveLevel())}")

        # build the set of instruction generators which compose the control system for this hive run
        # this ordering is important as the later managers will override any instructions from the previous
        # instruction generator for a specific vehicle id.
        instruction_generators = (
            BaseFleetManager(env.config.dispatcher),
            PositionFleetManager(
                demand_forecaster=BasicForecaster.build(env.config.input_config.demand_forecast_file),
                config=env.config.dispatcher,
            ),
            ChargingFleetManager(env.config.dispatcher),
            # DeluxeFleetManager(max_search_radius_km=env.config.network.max_search_radius_km),
            Dispatcher(env.config.dispatcher),
        )

        update = Update.build(env.config, instruction_generators)
        initial_payload = RunnerPayload(sim, env, update)

        log.info(f"running simulation for time {initial_payload.e.config.sim.start_time} "
                 f"to {initial_payload.e.config.sim.end_time}:")
        start = time.time()
        sim_result = LocalSimulationRunner.run(initial_payload)
        end = time.time()

        log.info(f'done! time elapsed: {round(end - start, 2)} seconds')

        _summary_stats(sim_result.s, env)

        env.reporter.close()

        if env.config.global_config.write_outputs:
            config_dump = env.config.asdict()
            dump_name = env.config.sim.sim_name + ".yaml"
            dump_path = os.path.join(env.config.scenario_output_directory, dump_name)
            with open(dump_path, 'w') as f:
                yaml.dump(config_dump, f, sort_keys=False)

        return 0

    except Exception as e:
        # perhaps in the future, a more robust handling here
        raise e


def _summary_stats(final_sim: SimulationState, env: Environment):
    """
    just some quick-and-dirty summary stats here
    :param sim: the final sim state
    """

    class VehicleResultsAccumulator(NamedTuple):
        balance: float = 0.0
        vkt: float = 0.0
        count: int = 0
        avg_soc: float = 0.0

        def add_vehicle(self, vehicle: Vehicle) -> VehicleResultsAccumulator:
            soc = env.mechatronics.get(vehicle.mechatronics_id).battery_soc(vehicle)
            return self._replace(
                balance=self.balance + vehicle.balance,
                vkt=self.vkt + vehicle.distance_traveled_km,
                count=self.count + 1,
                avg_soc=self.avg_soc + ((soc - self.avg_soc) / (self.count + 1)),
            )

    # collect all vehicle data
    v_acc = ft.reduce(
        lambda acc, veh: acc.add_vehicle(veh),
        final_sim.vehicles.values(),
        VehicleResultsAccumulator()
    )

    # collect all station data
    station_income = ft.reduce(
        lambda income, station: income + station.balance,
        final_sim.stations.values(),
        0.0
    )

    log.info(f"STATION  CURRENCY BALANCE:             $ {station_income:.2f}")
    log.info(f"FLEET    CURRENCY BALANCE:             $ {v_acc.balance:.2f}")
    log.info(f"         VEHICLE KILOMETERS TRAVELED:    {v_acc.vkt:.2f}")
    log.info(f"         AVERAGE FINAL SOC:              {v_acc.avg_soc * 100:.2f}%")


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
