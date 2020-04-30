from __future__ import annotations

import argparse
import functools as ft
import logging
import os
import time
from typing import NamedTuple

import yaml
from pkg_resources import resource_filename

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

root_log = logging.getLogger()
log = logging.getLogger(__name__)

parser = argparse.ArgumentParser(description="run hive")
parser.add_argument(
    'scenario_file',
    help='which scenario file to run. must live in hive.resources.scenarios',
)
parser.add_argument(
    '--path',
    dest='scenario_path',
    action='store_true',
    help='optional flag to specify a scenario file outside hive.resources.scenarios'
)


def run() -> int:
    """
    entry point for a hive application run
    :return: 0 if success, 1 if error
    """

    _welcome_to_hive()
    args = parser.parse_args()

    if not args.scenario_file:
        log.error("please specify a scenario file to run.")
        return 1

    try:
        if args.scenario_path:
            scenario_path = args.scenario_file
        else:
            scenario_path = resource_filename('hive.resources.scenarios', args.scenario_file)

        try:
            sim, env = load_simulation(scenario_path)
        except FileNotFoundError as fe:
            log.error(fe)
            return 1

        # initialize logging file handler
        log_fh = logging.FileHandler(os.path.join(env.config.output_directory, 'run.log'))
        formatter = logging.Formatter("[%(levelname)s] - %(name)s - %(message)s")
        log_fh.setFormatter(formatter)
        root_log.addHandler(log_fh)

        log.info(f"successfully loaded config: {args.scenario_file}")

        # build the set of instruction generators which compose the control system for this hive run

        # this ordering is important as the later managers will override any instructions from the previous
        # instruction generator for a specific vehicle id.
        instruction_generators = (
            BaseFleetManager(env.config.dispatcher),
            PositionFleetManager(
                demand_forecaster=BasicForecaster.build(env.config.io.file_paths.demand_forecast_file),
                config=env.config.dispatcher,
            ),
            ChargingFleetManager(env.config.dispatcher),
            # DeluxeFleetManager(max_search_radius_km=env.config.network.max_search_radius_km),
            Dispatcher(env.config.dispatcher),
        )

        update = Update.build(env.config.io, instruction_generators)
        initial_payload = RunnerPayload(sim, env, update)

        log.info(f"running simulation for time {initial_payload.e.config.sim.start_time} "
                 f"to {initial_payload.e.config.sim.end_time}:")
        start = time.time()
        sim_result = LocalSimulationRunner.run(initial_payload)
        end = time.time()

        log.info(f'done! time elapsed: {round(end - start, 2)} seconds')

        _summary_stats(sim_result.s)

        env.reporter.sim_log_file.close()

        config_dump = env.config.asdict()
        dump_name = env.config.sim.sim_name + ".yaml"
        dump_path = os.path.join(env.config.output_directory, dump_name)
        with open(dump_path, 'w') as f:
            yaml.dump(config_dump, f, sort_keys=False)

        return 0

    except Exception as e:
        # perhaps in the future, a more robust handling here
        raise e


def _summary_stats(final_sim: SimulationState):
    """
    just some quick-and-dirty summary stats here
    :param sim: the final sim state
    """

    class VehicleResultsAccumulator(NamedTuple):
        balance: float = 0.0
        vkt: float = 0.0
        avg_soc: float = 0.0
        count: int = 0

        def add_vehicle(self, vehicle: Vehicle) -> VehicleResultsAccumulator:
            return self._replace(
                balance=self.balance + vehicle.balance,
                vkt=self.vkt + vehicle.distance_traveled_km,
                avg_soc=self.avg_soc + ((vehicle.energy_source.soc - self.avg_soc) / (self.count + 1)),
                count=self.count + 1
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
    log.info(f"         AVERAGE FINAL SOC:              {v_acc.avg_soc * 100.0:.2f}%")


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
