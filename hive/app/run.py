from __future__ import annotations

import functools as ft
import logging
import os
import sys
import time
from typing import NamedTuple

from pkg_resources import resource_filename

from hive.dispatcher.forecaster.basic_forecaster import BasicForecaster
from hive.dispatcher.instruction_generator.base_fleet_manager import BaseFleetManager
from hive.dispatcher.instruction_generator.charging_fleet_manager import ChargingFleetManager
from hive.dispatcher.instruction_generator.dispatcher import Dispatcher
from hive.dispatcher.instruction_generator.position_fleet_manager import PositionFleetManager
from hive.dispatcher.instruction_generator.deluxe_fleet_manager import DeluxeFleetManager
from hive.runner.local_simulation_runner import LocalSimulationRunner
from hive.runner.runner_payload import RunnerPayload
from hive.model.vehicle import Vehicle
from hive.state.simulation_state.simulation_state import SimulationState
from hive.runner.load import load_simulation
from hive.state.simulation_state.update import Update
from hive.app.logging_config import LOGGING_CONFIG

root_log = logging.getLogger()
log = logging.getLogger(__name__)


def run() -> int:
    """
    entry point for a hive application run
    :return: 0 if success, 1 if error
    """

    _welcome_to_hive()

    if len(sys.argv) == 1:
        log.info("please specify a scenario file to run.")
        return 1

    try:
        scenario_file = sys.argv[1]

        cwd = os.getcwd()
        scenario_path = scenario_file if os.path.isfile(scenario_file) else f"{cwd}/{scenario_file}"

        sim, env = load_simulation(scenario_path)

        log_fh = logging.FileHandler(os.path.join(env.config.output_directory, 'run.log'))
        formatter = logging.Formatter(LOGGING_CONFIG['formatters']['simple']['format'])
        log_fh.setFormatter(formatter)
        root_log.addHandler(log_fh)

        log.info(f"successfully loaded config: {scenario_file}")

        # dispatcher = BasicDispatcher.build(environment.config.io, environment.config.dispatcher)

        demand_forecast_file = resource_filename("hive.resources.demand_forecast", env.config.io.demand_forecast_file)

        # this ordering is important as the later managers will override any instructions from the previous
        # instruction generator for a specific vehicle id.
        instruction_generators = (
            # BaseFleetManager(env.config.dispatcher.base_vehicles_charging_limit),
            # PositionFleetManager(
            #     demand_forecaster=BasicForecaster.build(demand_forecast_file),
            #     update_interval_seconds=env.config.dispatcher.fleet_sizing_update_interval_seconds
            # ),
            # ChargingFleetManager(env.config.dispatcher.charging_low_soc_threshold,
            #                      env.config.dispatcher.charging_max_search_radius_km),
            DeluxeFleetManager(),
            Dispatcher(env.config.dispatcher.matching_low_soc_threshold),
        )

        update = Update.build(env.config.io, instruction_generators)
        initial_payload = RunnerPayload(sim, env, update)

        start = time.time()
        sim_result = LocalSimulationRunner.run(initial_payload)
        end = time.time()

        log.info("\n")
        log.info(f'done! time elapsed: {round(end - start, 2)} seconds')

        _summary_stats(sim_result.s)

        env.reporter.sim_log_file.close()

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

    log.info("\n")
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
