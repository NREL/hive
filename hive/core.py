import pandas as pd
import os
from datetime import timedelta

from hive import preprocess as pp
from hive import tripenergy as nrg
from hive import charging as chrg
from hive import router
from hive import reporting
from hive.utils import Clock, assert_constraint, build_output_dir, info, progress_bar
from hive.initialize import initialize_stations, initialize_fleet
from hive.vehicle import Vehicle
from hive.dispatcher import Dispatcher
from hive.constraints import ENV_PARAMS, FLEET_STATE_IDX

class SimulationEngine:
    """
    Simulation engine for running hive simulations.

    Parameters
    ----------
    input_data: dict
        Dictionary containing all of the input data hive needs to run scenario.
        Use hive.helpers.load_scenario to generate this from scenario.yaml file
    """

    def __init__(self, input_data):
        self._SIM_ENV = None

        self.input_data = input_data


    def _build_simulation_env(self):
        SIM_ENV = {}

        #Load requests
        info("Processing requests..")
        reqs_df = self.input_data['requests']
        info("{} requests loaded".format(len(reqs_df)))

        #Filter requests where distance < min_miles
        reqs_df = pp.filter_short_distance_trips(reqs_df, min_miles=0.05)
        info("filtered requests violating min distance req, {} remain".format(len(reqs_df)))
        #
        #Filter requests where total time < min_time_s
        reqs_df = pp.filter_short_time_trips(reqs_df, min_time_s=1)
        info("filtered requests violating min time req, {} remain".format(len(reqs_df)))
        #

        SIM_ENV['requests'] = reqs_df

        sim_start_time = reqs_df.pickup_time.min()
        sim_end_time = reqs_df.dropoff_time.max()
        sim_time_steps = pd.date_range(
                                sim_start_time,
                                sim_end_time,
                                freq='{}S'.format(self.input_data['SIMULATION_PERIOD_SECONDS'])
                                )
        SIM_ENV['sim_time_steps'] = sim_time_steps

        sim_clock = Clock(
                        timestep_s = self.input_data['SIMULATION_PERIOD_SECONDS'],
                        datetime_steps = sim_time_steps,
                        )
        SIM_ENV['sim_clock'] = sim_clock

        #Calculate network scaling factor & average dispatch speed
        RN_SCALING_FACTOR = pp.calculate_road_vmt_scaling_factor(reqs_df)
        DISPATCH_MPH = pp.calculate_average_driving_speed(reqs_df)

        #TODO: Pool requests - from hive.pool, module for various pooling types - o/d, dynamic, n/a
        #TODO: reqs_df.to_csv(self.input_data['OUT_PATH'] + sim_name + 'requests/' + requests_filename, index=False)

        #Load charging network
        info("Loading charge network..")
        stations = initialize_stations(self.input_data['stations'], sim_clock)
        SIM_ENV['stations'] = stations

        bases = initialize_stations(self.input_data['bases'], sim_clock)
        SIM_ENV['bases'] = bases
        info("loaded {0} stations & {1} bases".format(len(stations), len(bases)))


        #Initialize vehicle fleet
        info("Initializing vehicle fleet..")
        env_params = {
            'MAX_DISPATCH_MILES': float(self.input_data['main']['MAX_DISPATCH_MILES']),
            'MIN_ALLOWED_SOC': float(self.input_data['main']['MIN_ALLOWED_SOC']),
            'RN_SCALING_FACTOR': RN_SCALING_FACTOR,
            'DISPATCH_MPH': DISPATCH_MPH,
            'LOWER_SOC_THRESH_STATION': float(self.input_data['main']['LOWER_SOC_THRESH_STATION']),
            'UPPER_SOC_THRESH_STATION': float(self.input_data['main']['UPPER_SOC_THRESH_STATION']),
            'MAX_ALLOWABLE_IDLE_MINUTES': float(self.input_data['main']['MAX_ALLOWABLE_IDLE_MINUTES']),
        }

        for param, val in env_params.items():
            assert_constraint(param, val, ENV_PARAMS, context="Environment Parameters")

        env_params['FLEET_STATE_IDX'] = FLEET_STATE_IDX
        SIM_ENV['env_params'] = env_params

        vehicle_types = [veh for veh in self.input_data['vehicles'].itertuples()]
        fleet, fleet_state = initialize_fleet(vehicle_types = vehicle_types,
                                 bases = bases,
                                 charge_curve = self.input_data['charge_curves'],
                                 whmi_lookup = self.input_data['whmi_lookup'],
                                 start_time = reqs_df.pickup_time.iloc[0],
                                 env_params = env_params,
                                 clock = sim_clock)
        info("{} vehicles initialized".format(len(fleet)))
        SIM_ENV['fleet'] = fleet

        info("Initializing route engine..")
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

        info("Initializing dispatcher..")
        dispatcher = Dispatcher(fleet = fleet,
                                fleet_state = fleet_state,
                                stations = stations,
                                bases = bases,
                                env_params = env_params,
                                route_engine = route_engine,
                                clock = sim_clock)
        SIM_ENV['dispatcher'] = dispatcher




        self._SIM_ENV = SIM_ENV

    def run_simulation(self, sim_name, out_path = ''):
        """
        Runs a single hive simulation.

        Parameters
        ----------
        sim_name: string
            Name of simulation
        out_path: string
            Where this function will write output logs.
        """
        info("Building scenario output directory..")
        output_file_paths = build_output_dir(sim_name, out_path)

        vehicle_summary_file = os.path.join(output_file_paths['summary_path'], 'vehicle_summary.csv')
        fleet_summary_file = os.path.join(output_file_paths['summary_path'], 'fleet_summary.txt')
        station_summary_file = os.path.join(output_file_paths['summary_path'], 'station_summary.csv')

        self._build_simulation_env()

        total_iterations = len(self._SIM_ENV['sim_time_steps'])-1
        i = 0

        info("Simulating {}..".format(sim_name))
        reqs_df = self._SIM_ENV['requests']

        for timestep in self._SIM_ENV['sim_time_steps']:
            progress_bar(i, total_iterations)
            i+=1
            requests = reqs_df[(timestep <= reqs_df.pickup_time) \
                & (reqs_df.pickup_time < (timestep + timedelta(seconds=self.input_data['SIMULATION_PERIOD_SECONDS'])))]
            self._SIM_ENV['dispatcher'].process_requests(requests)

            for veh in self._SIM_ENV['fleet']:
                veh.step()

            for station in self._SIM_ENV['stations']:
                station.step()

            for base in self._SIM_ENV['bases']:
                base.step()

            next(self._SIM_ENV['sim_clock'])

        info("Done Simulating")
        info("Generating logs and summary statistics..")

        reporting.generate_logs(self._SIM_ENV['fleet'], output_file_paths['vehicle_path'], 'vehicle')
        reporting.generate_logs(self._SIM_ENV['stations'], output_file_paths['station_path'], 'station')
        reporting.generate_logs(self._SIM_ENV['bases'], output_file_paths['base_path'], 'base')
        reporting.generate_logs([self._SIM_ENV['dispatcher']], output_file_paths['dispatcher_path'], 'dispatcher')

        reporting.summarize_fleet_stats(output_file_paths['vehicle_path'], output_file_paths['summary_path'])
        reporting.summarize_dispatcher(output_file_paths['dispatcher_path'], output_file_paths['summary_path'])
