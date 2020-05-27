from __future__ import annotations

import argparse
import functools as ft
import logging
import os
import time
from typing import NamedTuple, TYPE_CHECKING

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

log = logging.getLogger("hive")
# log = logging.getLogger(__name__)

parser = argparse.ArgumentParser(description="run hive")
parser.add_argument(
    'scenario_file',
    help='which scenario file to run (try "denver_downtown.yaml" or "manhattan.yaml")'
)


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
        return 1

    # main application
    try:

        # create the configuration and load the simulation
        try:
            scenario_file = fs.find_scenario(args.scenario_file)
            sim, env = load_simulation(scenario_file)
        except FileNotFoundError as fe:
            log.error(fe)
            return 1

        # initialize logging file handler
        if env.config.global_config.log_run:
            run_log_path = os.path.join(env.config.scenario_output_directory, 'run.log')
            log_fh = logging.FileHandler(run_log_path)
            formatter = logging.Formatter("[%(levelname)s] - %(name)s - %(message)s")
            log_fh.setFormatter(formatter)
            log.addHandler(log_fh)
            log.info(f"creating run log at {run_log_path}")

        log.info(f"successfully loaded config at {args.scenario_file}")
        log.info(f"global hive configuration loaded from {env.config.global_config.global_settings_file_path}:")
        for k, v in env.config.global_config.asdict().items():
            log.info(f"  {k}: {v}")
        log.info(f"output directory set to {env.config.scenario_output_directory}")

        # build the set of instruction generators which compose the control system for this hive run
        # this ordering is important as the later managers will override any instructions from the previous
        # instruction generator for a specific vehicle id.
        instruction_generators = (
            BaseFleetManager(env.config.dispatcher),
            PositionFleetManager(
                demand_forecaster=BasicForecaster.build(env.config.input.demand_forecast_file),
                config=env.config.dispatcher,
            ),
            ChargingFleetManager(env.config.dispatcher),
            # DeluxeFleetManager(max_search_radius_km=env.config.network.max_search_radius_km),
            Dispatcher(env.config.dispatcher),
        )

        update = Update.build(env.config.input, instruction_generators)
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


if __name__ == "__main__":
    run()
