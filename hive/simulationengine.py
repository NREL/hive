import logging
from logging.handlers import RotatingFileHandler
import os
from datetime import timedelta

import pandas as pd
import geopandas as gpd

from hive import preprocess as pp
from hive import reporting
from hive import router
from hive.constraints import ENV_PARAMS, FLEET_STATE_IDX
from hive.dispatcher import Dispatcher
from hive.manager import Manager
from hive.initialize import initialize_stations, initialize_fleet
from hive.utils import (
    Clock,
    assert_constraint,
    build_output_dir,
    progress_bar,
    )


class SimulationEngine:
    """
    Simulation engine for running hive simulations.

    Parameters
    ----------
    input_data: dict
        Dictionary containing all of the input data hive needs to run scenario.
        Use hive.helpers.load_scenario to generate this from scenario.yaml file
    """

    def __init__(self, input_data=None, out_path=''):
        self.log = logging.getLogger('run_log')

        formatter = logging.Formatter("[%(levelname)s] %(asctime)s - %(message)s")
        run_handler = RotatingFileHandler(os.path.join(out_path, 'run.log'))
        run_handler.setFormatter(formatter)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)

        self.log.addHandler(run_handler)
        self.log.addHandler(console_handler)
        self.log.setLevel(logging.INFO)

        self._SIM_ENV = None

        self.input_data = input_data
        self.out_path = out_path

    def _build_simulation_env(self, output_file_paths):
        SIM_ENV = {}

        # Load requests
        self.log.info("Processing requests..")
        reqs_df = self.input_data['requests']
        self.log.info("{} requests loaded".format(len(reqs_df)))

        # Filter requests where distance < min_miles
        reqs_df = pp.filter_short_distance_trips(reqs_df, min_miles=0.05)
        self.log.info("filtered requests violating min distance req, {} remain".format(len(reqs_df)))

        # Filter requests where total time < min_time_s
        reqs_df = pp.filter_short_time_trips(reqs_df, min_time_s=1)
        self.log.info("filtered requests violating min time req, {} remain".format(len(reqs_df)))

        SIM_ENV['requests'] = reqs_df

        self.log.info("Calculating demand..")
        demand = pp.calculate_demand(reqs_df, self.input_data['SIMULATION_PERIOD_SECONDS'])
        SIM_ENV['demand'] = demand

        sim_start_time = reqs_df.pickup_time.min()
        sim_end_time = reqs_df.dropoff_time.max()
        sim_time_steps = pd.date_range(
            sim_start_time,
            sim_end_time,
            freq='{}S'.format(self.input_data['SIMULATION_PERIOD_SECONDS'])
        )
        SIM_ENV['sim_time_steps'] = sim_time_steps

        sim_clock = Clock(
            timestep_s=self.input_data['SIMULATION_PERIOD_SECONDS'],
            datetime_steps=sim_time_steps,
        )
        SIM_ENV['sim_clock'] = sim_clock

        # Calculate network scaling factor & average dispatch speed
        RN_SCALING_FACTOR = pp.calculate_road_vmt_scaling_factor(reqs_df)
        DISPATCH_MPH = pp.calculate_average_driving_speed(reqs_df)

        # TODO: Pool requests - from hive.pool, module for various pooling types - o/d, dynamic, n/a
        # TODO: reqs_df.to_csv(self.input_data['OUT_PATH'] + sim_name + 'requests/' + requests_filename, index=False)

        # Load charging network
        station_log = None
        if 'stations' in self.input_data['LOGS']:
            station_log = logging.getLogger('station_log')
            station_log_file = os.path.join(output_file_paths['station_path'], 'station.csv')
            fh = RotatingFileHandler(
                            station_log_file,
                            maxBytes = 100000000,
                            backupCount = 100,)

            formatter = logging.Formatter("%(message)s")
            fh.setFormatter(formatter)
            station_log.handlers = [fh]
            station_log.setLevel(logging.INFO)

        self.log.info("Loading charge network..")
        stations = initialize_stations(self.input_data['stations'], sim_clock, station_log)
        SIM_ENV['stations'] = stations

        base_log = None
        if 'bases' in self.input_data['LOGS']:
            base_log = logging.getLogger('base_log')
            base_log_file = os.path.join(output_file_paths['base_path'], 'base.csv')
            fh = RotatingFileHandler(
                            base_log_file,
                            maxBytes = 100000000,
                            backupCount = 100,)

            formatter = logging.Formatter("%(message)s")
            fh.setFormatter(formatter)
            base_log.handlers = [fh]
            base_log.setLevel(logging.INFO)

        bases = initialize_stations(self.input_data['bases'], sim_clock, base_log)
        SIM_ENV['bases'] = bases
        self.log.info("loaded {0} stations & {1} bases".format(len(stations), len(bases)))

        # Initialize vehicle fleet
        self.log.info("Initializing vehicle fleet..")
        env_params = {
            'MAX_DISPATCH_MILES': float(self.input_data['main']['MAX_DISPATCH_MILES']),
            'MIN_ALLOWED_SOC': float(self.input_data['main']['MIN_ALLOWED_SOC']),
            'RN_SCALING_FACTOR': RN_SCALING_FACTOR,
            'DISPATCH_MPH': DISPATCH_MPH,
            'LOWER_SOC_THRESH_STATION': float(self.input_data['main']['LOWER_SOC_THRESH_STATION']),
            'UPPER_SOC_THRESH_STATION': float(self.input_data['main']['UPPER_SOC_THRESH_STATION']),
            'MAX_ALLOWABLE_IDLE_MINUTES': float(self.input_data['main']['MAX_ALLOWABLE_IDLE_MINUTES'])
        }

        for param, val in env_params.items():
            assert_constraint(param, val, ENV_PARAMS, context="Environment Parameters")

        env_params['FLEET_STATE_IDX'] = FLEET_STATE_IDX

        # operating area used for location sampling
        env_params['operating_area_file_path'] = self.input_data['OPERATING_AREA_FILE']

        SIM_ENV['env_params'] = env_params

        vehicle_log = None
        if 'vehicles' in self.input_data['LOGS']:
            vehicle_log = logging.getLogger('vehicle_log')
            vehicle_log_file = os.path.join(output_file_paths['vehicle_path'], 'vehicle.csv')
            fh = RotatingFileHandler(
                            vehicle_log_file,
                            maxBytes = 100000000,
                            backupCount = 100,)

            formatter = logging.Formatter("%(message)s")
            fh.setFormatter(formatter)
            vehicle_log.handlers = [fh]
            vehicle_log.setLevel(logging.INFO)

        vehicle_types = [veh for veh in self.input_data['vehicles'].itertuples()]
        fleet, fleet_state = initialize_fleet(vehicle_types=vehicle_types,
                                              bases=bases,
                                              charge_curve=self.input_data['charge_curves'],
                                              whmi_lookup=self.input_data['whmi_lookup'],
                                              start_time=reqs_df.pickup_time.iloc[0],
                                              env_params=env_params,
                                              clock=sim_clock,
                                              vehicle_log=vehicle_log)
        self.log.info("{} vehicles initialized".format(len(fleet)))
        SIM_ENV['fleet'] = fleet

        self.log.info("Initializing route engine..")
        if self.input_data['USE_OSRM']:
            route_engine = router.OSRMRouteEngine(
                self.input_data['OSRM_SERVER'],
                self.input_data['SIMULATION_PERIOD_SECONDS'])
        else:
            route_engine = router.DefaultRouteEngine(
                self.input_data['SIMULATION_PERIOD_SECONDS'],
                env_params['RN_SCALING_FACTOR'],
                env_params['DISPATCH_MPH'],
            )

        # load dispatcher algorithms, or if not provided, use the defaults
        if 'ASSIGNMENT' in self.input_data['main']:
            active_servicing_name = self.input_data['main']['ASSIGNMENT']
        else:
            active_servicing_name = "greedy"
        if 'REPOSITIONING' in self.input_data['main']:
            active_fleet_mgmt_name = self.input_data['main']['REPOSITIONING']
        else:
            active_fleet_mgmt_name = "basic"
        if 'ACTIVE_CHARGING' in self.input_data['main']:
            active_charging_name = self.input_data['main']['ACTIVE_CHARGING']
        else:
            active_charging_name = "basic"
        if 'INACTIVE_MGMT' in self.input_data['main']:
            inactive_fleet_mgmt_name = self.input_data['main']['INACTIVE_MGMT']
        else:
            inactive_fleet_mgmt_name = "basic"

        self.log.info("dispatcher loading {} assignment module".format(active_servicing_name))
        self.log.info("dispatcher loading {} repositioning module".format(active_fleet_mgmt_name))
        self.log.info("dispatcher loading {} charging module".format(active_charging_name))
        self.log.info("dispatcher loading {} inactive fleet management module".format(inactive_fleet_mgmt_name))

        dispatcher_log = None
        if 'dispatcher' in self.input_data['LOGS']:
            dispatcher_log = logging.getLogger('dispatcher_log')
            dispatcher_log_file = os.path.join(output_file_paths['dispatcher_path'], 'dispatcher.csv')
            fh = RotatingFileHandler(
                            dispatcher_log_file,
                            maxBytes = 100000000,
                            backupCount = 100,)

            formatter = logging.Formatter("%(message)s")
            fh.setFormatter(formatter)
            dispatcher_log.handlers = [fh]
            dispatcher_log.setLevel(logging.INFO)

        dispatcher = Dispatcher(
            inactive_fleet_mgmt_name,
            active_fleet_mgmt_name,
            active_servicing_name,
            active_charging_name,
            fleet,
            fleet_state,
            stations,
            bases,
            demand,
            env_params,
            route_engine,
            sim_clock,
            dispatcher_log
        )

        SIM_ENV['dispatcher'] = dispatcher

        manager = Manager(
            fleet,
            fleet_state,
            demand,
            env_params,
            sim_clock,
        )

        SIM_ENV['manager'] = manager

        self._SIM_ENV = SIM_ENV

    def run_simulation(self, sim_name):
        """
        Runs a single hive simulation.

        Parameters
        ----------
        sim_name: string
            Name of simulation
        out_path: string
            Where this function will write output logs.
        """
        self.log.info("Building scenario output directory..")
        output_file_paths = build_output_dir(sim_name, self.out_path)

        self._build_simulation_env(output_file_paths)

        total_iterations = len(self._SIM_ENV['sim_time_steps']) - 1
        i = 0

        self.log.info("Simulating {}..".format(sim_name))
        reqs_df = self._SIM_ENV['requests']

        for timestep in self._SIM_ENV['sim_time_steps']:
            progress_bar(i, total_iterations)
            i += 1
            requests = reqs_df[(timestep <= reqs_df.pickup_time) \
                               & (reqs_df.pickup_time < (
                        timestep + timedelta(seconds=self.input_data['SIMULATION_PERIOD_SECONDS'])))]

            active_fleet_n = self._SIM_ENV['manager'].calc_active_fleet_n()

            self._SIM_ENV['dispatcher'].balance_fleet(active_fleet_n)
            self._SIM_ENV['dispatcher'].step(requests)

            for veh in self._SIM_ENV['fleet']:
                veh.step()

            for station in self._SIM_ENV['stations']:
                station.step()

            for base in self._SIM_ENV['bases']:
                base.step()

            #TODO: This logging method stinks.... We should find a new way. NR
            self._SIM_ENV['dispatcher'].active_servicing_module.log()

            next(self._SIM_ENV['sim_clock'])

        self.log.info("Done Simulating")
