from __future__ import annotations

import os
import sys
import time
from datetime import datetime
from typing import NamedTuple

import yaml
from pkg_resources import resource_filename
import functools as ft

from hive.config import *
from hive.dispatcher.managed_dispatcher import ManagedDispatcher
from hive.dispatcher.forecaster.basic_forecaster import BasicForecaster
from hive.dispatcher.manager.basic_manager import BasicManager
from hive.model import Vehicle
from hive.reporting.detailed_reporter import DetailedReporter
from hive.runner.local_simulation_runner import LocalSimulationRunner
from hive.state.initialize_simulation import initialize_simulation
from hive.state.update import UpdateRequests, CancelRequests, StepSimulation
from hive.state.update import ChargingPriceUpdate
from hive.state.simulation_state import SimulationState


def run():
    """
    entry point for a hive run
    :return: 0 if success, 1 if error
    """

    _welcome_to_hive()

    if len(sys.argv) == 1:
        print("please specify a scenario file to run.")
        return 1

    try:
        scenario_file = sys.argv[1]
        print(f"attempting to load config: {scenario_file}")

        cwd = os.getcwd()
        scenario_path = scenario_file if os.path.isfile(scenario_file) else f"{cwd}/{scenario_file}"

        with open(scenario_path, 'r') as f:
            config_builder = yaml.safe_load(f)

        config = HiveConfig.build(config_builder)
        if isinstance(config, Exception):
            # perhaps in the future, more robust handling here
            raise config

        run_name = config.sim.sim_name + '_' + datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        sim_output_dir = os.path.join(config.io.working_directory, run_name)
        if not os.path.isdir(sim_output_dir):
            os.makedirs(sim_output_dir)

        print("initializing scenario")

        simulation_state, environment = initialize_simulation(config)

        requests_file = resource_filename("hive.resources.requests", config.io.requests_file)
        rate_structure_file = resource_filename("hive.resources.service_prices", config.io.rate_structure_file)
        charging_price_file = resource_filename("hive.resources.charging_prices", config.io.charging_price_file)

        manager = BasicManager(demand_forecaster=BasicForecaster())
        dispatcher = ManagedDispatcher.build(
            manager=manager,
            geofence_file=config.io.geofence_file,
        )

        # TODO: move this lower and make it ordered.
        update_functions = (
            ChargingPriceUpdate.build(charging_price_file),
            UpdateRequests.build(requests_file, rate_structure_file),
            CancelRequests(),
            StepSimulation(dispatcher),
        )

        runner = LocalSimulationRunner(env=environment)
        reporter = DetailedReporter(config.io, sim_output_dir)

        print("running HIVE")

        start = time.time()
        sim_result = runner.run(
            initial_simulation_state=simulation_state,
            update_functions=update_functions,
            reporter=reporter,
        )

        end = time.time()
        print("\n")
        print(f'done! time elapsed: {round(end - start, 2)} seconds')

        _summary_stats(sim_result.s)

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

    print("\n")
    print(f"STATION  CURRENCY BALANCE:             $ {station_income:.2f}")
    print(f"FLEET    CURRENCY BALANCE:             $ {v_acc.balance:.2f}")
    print(f"         VEHICLE KILOMETERS TRAVELED:    {v_acc.vkt:.2f}")
    print(f"         AVERAGE FINAL SOC:              {v_acc.avg_soc * 100.0:.2f}%")


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
    print(welcome)


if __name__ == "__main__":
    run()
