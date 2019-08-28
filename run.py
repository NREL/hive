"""
Run hive w/ inputs defined in config.py
"""
import subprocess
import os
import sys
import random
import shutil
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import pickle
import glob
import time
import yaml

import config as cfg

from hive import preprocess as pp
from hive import tripenergy as nrg
from hive import charging as chrg
from hive import utils
from hive import reporting
from hive.initialize import initialize_stations, initialize_fleet
from hive.vehicle import Vehicle
from hive.dispatcher import Dispatcher
from hive.constraints import ENV_PARAMS, FLEET_STATE_IDX


random.seed(cfg.RANDOM_SEED)
np.random.seed(cfg.RANDOM_SEED)
THIS_DIR = os.path.dirname(os.path.realpath(__file__))
LIB_PATH = os.path.join(THIS_DIR, cfg.IN_PATH, 'library')
SCENARIO_PATH = os.path.join(THIS_DIR, cfg.IN_PATH, 'scenarios')
STATIC_PATH = os.path.join(LIB_PATH, '.static')

OUT_PATH = os.path.join(THIS_DIR, cfg.OUT_PATH)



def load_scenario(scenario_file):

    def name(path):
        return os.path.splitext(os.path.basename(path))[0]

    scenario_name = name(scenario_file)
    with open(scenario_file, 'r') as f:
        yaml_data = yaml.safe_load(f)

        data = {}

        filepaths = yaml_data['filepaths']
        data['requests'] = pp.load_requests(filepaths['requests_file_path'])
        data['main'] = yaml_data['parameters']
        network_dtype = {
                        'longitude': "float64",
                        'latitude': "float64",
                        'plugs': "int64",
                        'plug_power_kw': "float64",
                        }
        data['stations'] = pd.DataFrame(yaml_data['stations']).astype(dtype=network_dtype)
        data['bases'] = pd.DataFrame(yaml_data['bases']).astype(dtype=network_dtype)

        vehicle_dtype = {
                        'BATTERY_CAPACITY_KWH': 'float64',
                        'PASSENGERS': 'int64',
                        'EFFICIENCY_WHMI': 'float64',
                        'MAX_KW_ACCEPTANCE': 'float64',
                        'NUM_VEHICLES': 'int64',
                        }
        data['vehicles'] = pd.DataFrame(yaml_data['vehicles']).astype(dtype=vehicle_dtype)

        data['charge_curves'] = pd.DataFrame(yaml_data['charge_profile'])
        data['whmi_lookup'] = pd.DataFrame(yaml_data['whmi_lookup'])


    return scenario_name, data

def build_simulation_env(data):
    SIM_ENV = {}

    #Load requests
    if cfg.VERBOSE: print("Processing requests..")
    reqs_df = data['requests']
    if cfg.VERBOSE: print("{} requests loaded".format(len(reqs_df)))

    #Filter requests where distance < min_miles
    reqs_df = pp.filter_short_distance_trips(reqs_df, min_miles=0.05)
    if cfg.VERBOSE: print("filtered requests violating min distance req, {} remain".format(len(reqs_df)))
    #
    #Filter requests where total time < min_time_s
    reqs_df = pp.filter_short_time_trips(reqs_df, min_time_s=1)
    if cfg.VERBOSE: print("filtered requests violating min time req, {} remain".format(len(reqs_df)))
    #

    SIM_ENV['requests'] = reqs_df

    sim_clock = utils.Clock(timestep_s = cfg.SIMULATION_PERIOD_SECONDS)
    SIM_ENV['sim_clock'] = sim_clock

    #Calculate network scaling factor & average dispatch speed
    RN_SCALING_FACTOR = pp.calculate_road_vmt_scaling_factor(reqs_df)
    DISPATCH_MPH = pp.calculate_average_driving_speed(reqs_df)

    #TODO: Pool requests - from hive.pool, module for various pooling types - o/d, dynamic, n/a
    #TODO: reqs_df.to_csv(cfg.OUT_PATH + sim_name + 'requests/' + requests_filename, index=False)

    #Load charging network
    if cfg.VERBOSE: print("Loading charge network..")
    stations = initialize_stations(data['stations'], sim_clock)
    SIM_ENV['stations'] = stations

    bases = initialize_stations(data['bases'], sim_clock)
    SIM_ENV['bases'] = bases
    if cfg.VERBOSE: print("loaded {0} stations & {1} bases".format(len(stations), len(bases)), "", sep="\n")


    #Initialize vehicle fleet
    if cfg.VERBOSE: print("Initializing vehicle fleet..", "", sep="\n")
    env_params = {
        'MAX_DISPATCH_MILES': float(data['main']['MAX_DISPATCH_MILES']),
        'MIN_ALLOWED_SOC': float(data['main']['MIN_ALLOWED_SOC']),
        'RN_SCALING_FACTOR': RN_SCALING_FACTOR,
        'DISPATCH_MPH': DISPATCH_MPH,
        'LOWER_SOC_THRESH_STATION': float(data['main']['LOWER_SOC_THRESH_STATION']),
        'UPPER_SOC_THRESH_STATION': float(data['main']['UPPER_SOC_THRESH_STATION']),
        'MAX_ALLOWABLE_IDLE_MINUTES': float(data['main']['MAX_ALLOWABLE_IDLE_MINUTES']),
    }

    for param, val in env_params.items():
        utils.assert_constraint(param, val, ENV_PARAMS, context="Environment Parameters")

    env_params['FLEET_STATE_IDX'] = FLEET_STATE_IDX
    SIM_ENV['env_params'] = env_params

    vehicle_types = [veh for veh in data['vehicles'].itertuples()]
    fleet, fleet_state = initialize_fleet(vehicle_types = vehicle_types,
                             bases = bases,
                             charge_curve = data['charge_curves'],
                             whmi_lookup = data['whmi_lookup'],
                             start_time = reqs_df.pickup_time.iloc[0],
                             env_params = env_params,
                             clock = sim_clock)
    if cfg.VERBOSE: print("{} vehicles initialized".format(len(fleet)), "", sep="\n")
    SIM_ENV['fleet'] = fleet

    dispatcher = Dispatcher(fleet = fleet,
                            fleet_state = fleet_state,
                            stations = stations,
                            bases = bases,
                            env_params = env_params,
                            clock = sim_clock)
    SIM_ENV['dispatcher'] = dispatcher

    sim_start_time = reqs_df.pickup_time.min()
    sim_end_time = reqs_df.dropoff_time.max()
    sim_time_steps = pd.date_range(sim_start_time, sim_end_time, freq='{}S'.format(cfg.SIMULATION_PERIOD_SECONDS))
    SIM_ENV['sim_time_steps'] = sim_time_steps

    return SIM_ENV


def run_simulation(data, sim_name):

    if cfg.VERBOSE: print("", "#"*30, "Preparing {}".format(sim_name), "#"*30, "", sep="\n")

    if cfg.VERBOSE: print("Building scenario output directory..", "", sep="\n")
    output_file_paths = utils.build_output_dir(sim_name, OUT_PATH)

    vehicle_summary_file = os.path.join(output_file_paths['summary_path'], 'vehicle_summary.csv')
    fleet_summary_file = os.path.join(output_file_paths['summary_path'], 'fleet_summary.txt')
    station_summary_file = os.path.join(output_file_paths['summary_path'], 'station_summary.csv')

    SIM_ENV = build_simulation_env(data)

    total_iterations = len(SIM_ENV['sim_time_steps'])
    i = 0

    if cfg.VERBOSE: print("#"*30, "Simulating {}".format(sim_name), "#"*30, "", sep="\n")
    reqs_df = SIM_ENV['requests']
    for timestep in SIM_ENV['sim_time_steps']:
        i+=1
        if i%100 == 0:
            print("{} of {} iterations completed.".format(i, total_iterations))
        requests = reqs_df[(timestep <= reqs_df.pickup_time) \
            & (reqs_df.pickup_time < (timestep + timedelta(seconds=cfg.SIMULATION_PERIOD_SECONDS)))]
        SIM_ENV['dispatcher'].process_requests(requests)

        for veh in SIM_ENV['fleet']:
            veh.step()

        for station in SIM_ENV['stations']:
            station.step()

        for base in SIM_ENV['bases']:
            base.step()

        next(SIM_ENV['sim_clock'])

    if cfg.VERBOSE: print("Generating logs and summary statistics..")

    reporting.generate_logs(SIM_ENV['fleet'], output_file_paths['vehicle_path'], 'vehicle')
    reporting.generate_logs(SIM_ENV['stations'], output_file_paths['station_path'], 'station')
    reporting.generate_logs(SIM_ENV['bases'], output_file_paths['base_path'], 'base')
    reporting.generate_logs([SIM_ENV['dispatcher']], output_file_paths['dispatcher_path'], 'dispatcher')

    reporting.summarize_fleet_stats(output_file_paths['vehicle_path'], output_file_paths['summary_path'])

if __name__ == "__main__":
    if not os.path.isdir(OUT_PATH):
        print('Building base output directory..')
        os.makedirs(cfg.OUT_PATH)

    assert len(cfg.SCENARIOS) == len(set(cfg.SCENARIOS)), 'Scenario names must be unique.'


    all_scenarios = glob.glob(os.path.join(SCENARIO_PATH, '*.yaml'))

    for scenario_file in all_scenarios:
        scenario_name, data = load_scenario(scenario_file)
        if scenario_name in cfg.SCENARIOS:
            run_simulation(data, scenario_name)
