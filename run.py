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

import config as cfg

from hive import preprocess as pp
from hive import tripenergy as nrg
from hive import charging as chrg
from hive import utils
from hive import reporting
from hive.initialize import initialize_stations, initialize_bases, initialize_fleet
from hive.vehicle import Vehicle
from hive.dispatcher import Dispatcher
from hive.constraints import ENV_PARAMS


seed = 123
random.seed(seed)
np.random.seed(seed)
THIS_DIR = os.path.dirname(os.path.realpath(__file__))
SCENARIO_PATH = os.path.join(THIS_DIR, cfg.IN_PATH, '.scenarios', cfg.SIMULATION_NAME.replace(" ", "_"))
OUT_PATH = os.path.join(THIS_DIR, cfg.OUT_PATH, cfg.SIMULATION_NAME.replace(" ", "_"))
LIB_PATH = os.path.join(cfg.IN_PATH, '.lib')

FLEET_STATE_IDX ={
    'x': 0,
    'y': 1,
    'active': 2,
    'available': 3,
    'soc': 4,
    'idle_min': 5,
    'KWH__MI': 6,
    'BATTERY_CAPACITY_KWH': 7,
}

def build_input_files():
    scenarios = dict()

    main_file = os.path.join(cfg.IN_PATH, 'main.csv')
    charge_file = os.path.join(LIB_PATH, 'raw_leaf_curves.csv')
    whmi_lookup_file = os.path.join(LIB_PATH, 'wh_mi_lookup.csv')
    charge_df = pd.read_csv(charge_file)
    sim_df = pd.read_csv(main_file)
    whmi_df = pd.read_csv(whmi_lookup_file)

    scenario_names = list()

    for i, row in sim_df.iterrows():
        row["SCENARIO_NAME"] = row["SCENARIO_NAME"].strip().replace(" ", "_")
        scenario_names.append(row['SCENARIO_NAME'])
        data = {}
        file_deps = [main_file, charge_file, whmi_lookup_file]

        req_file = os.path.join(cfg.IN_PATH, 'requests', row['REQUESTS_FILE'])
        file_deps.append(req_file)

        # Path to charge network file
        charge_stations_file = os.path.join(cfg.IN_PATH, 'charge_network', row['CHARGE_STATIONS_FILE'])
        veh_bases_file = os.path.join(cfg.IN_PATH, 'charge_network', row['VEH_BASES_FILE'])
        file_deps.append(charge_stations_file)

        fleet_file = os.path.join(cfg.IN_PATH, 'fleets', row['FLEET_FILE'])
        file_deps.append(fleet_file)

        fleet_df = pd.read_csv(fleet_file)
        assert fleet_df.shape[0] > 0, 'Must have at least one vehicle type to run simulation.'
        row['TOTAL_NUM_VEHICLES'] = fleet_df.NUM_VEHICLES.sum()
        row['NUM_VEHICLE_TYPES'] = fleet_df.shape[0]

        veh_keys = []

        for veh in fleet_df.itertuples():
            veh_file = os.path.join(cfg.IN_PATH, 'vehicles', '{}.csv'.format(veh.VEHICLE_NAME))
            veh_df = pd.read_csv(veh_file)
            veh_df['VEHICLE_NAME'] = veh.VEHICLE_NAME
            veh_df['NUM_VEHICLES'] = veh.NUM_VEHICLES
            data[veh.VEHICLE_NAME] = veh_df.iloc[0]
            veh_keys.append(veh.VEHICLE_NAME)

        row['VEH_KEYS'] = veh_keys

        data['requests'] = pp.load_requests(req_file)
        data['stations'] = pd.read_csv(charge_stations_file)
        data['bases'] = pd.read_csv(veh_bases_file)
        data['main'] = row
        data['charge_curves'] = charge_df
        data['whmi_lookup'] = whmi_df

        scenarios[row['SCENARIO_NAME']] = data

    assert len(scenario_names) == len(set(scenario_names)), 'Scenario names must be unique.'

    return scenarios


def run_simulation(data, sim_name, infile=None):
    if infile is not None:
        with open(infile, 'rb') as f:
            data = pickle.load(f)

    vehicle_log_file = os.path.join(OUT_PATH, sim_name, 'logs', 'vehicle_log.csv')
    station_charging_log_file = os.path.join(OUT_PATH, sim_name, 'logs', 'station_charging_log.csv')
    base_charging_log_file = os.path.join(OUT_PATH, sim_name, 'logs', 'base_charging_log.csv')
    failed_requests_log_file = os.path.join(OUT_PATH, sim_name, 'logs', 'failed_requests_logs.csv')

    vehicle_summary_file = os.path.join(OUT_PATH, sim_name, 'summaries', 'vehicle_summary.csv')
    fleet_summary_file = os.path.join(OUT_PATH, sim_name, 'summaries', 'fleet_summary.txt')
    station_summary_file = os.path.join(OUT_PATH, sim_name, 'summaries', 'station_summary.csv')

    if cfg.VERBOSE: print("", "#"*30, "Preparing {}".format(sim_name), "#"*30, "", sep="\n")

    if cfg.VERBOSE: print("Reading input files..", "", sep="\n")
    inputs = data['main']

    if cfg.VERBOSE: print("Building scenario output directory..", "", sep="\n")
    log_path, summary_path = utils.build_output_dir(sim_name, OUT_PATH)

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
    # #Filter requests where pickup/dropoff location outside operating area
    # shp_file = inputs['OPERATING_AREA_SHP']
    # oa_filepath = os.path.join(cfg.IN_PATH, 'operating_area', shp_file)
    # reqs_df = pp.filter_requests_outside_oper_area(reqs_df, oa_filepath)
    # if cfg.VERBOSE: print("filtered requests outside of operating area, {} remain".format(len(reqs_df)), "", sep="\n")

    #Calculate network scaling factor & average dispatch speed
    RN_SCALING_FACTOR = pp.calculate_road_vmt_scaling_factor(reqs_df)
    DISPATCH_MPH = pp.calculate_average_driving_speed(reqs_df)

    #TODO: Pool requests - from hive.pool, module for various pooling types - o/d, dynamic, n/a
    #TODO: reqs_df.to_csv(cfg.OUT_PATH + sim_name + 'requests/' + requests_filename, index=False)

    #Load charging network
    if cfg.VERBOSE: print("Loading charge network..")
    stations = initialize_stations(data['stations'], station_charging_log_file)
    bases = initialize_bases(data['bases'], base_charging_log_file)
    if cfg.VERBOSE: print("loaded {0} stations & {1} bases".format(len(stations), len(bases)), "", sep="\n")

    sim_clock = utils.Clock(timestep_s = cfg.SIMULATION_PERIOD_SECONDS)

    #Initialize vehicle fleet
    if cfg.VERBOSE: print("Initializing vehicle fleet..", "", sep="\n")
    env_params = {
        'MAX_DISPATCH_MILES': inputs['MAX_DISPATCH_MILES'],
        'MIN_ALLOWED_SOC': inputs['MIN_ALLOWED_SOC'],
        'RN_SCALING_FACTOR': RN_SCALING_FACTOR,
        'DISPATCH_MPH': DISPATCH_MPH,
        'LOWER_SOC_THRESH_STATION': inputs['LOWER_SOC_THRESH_STATION'],
        'UPPER_SOC_THRESH_STATION': inputs['UPPER_SOC_THRESH_STATION'],
        'MAX_ALLOWABLE_IDLE_MINUTES': inputs['MAX_ALLOWABLE_IDLE_MINUTES'],
    }

    for param, val in env_params.items():
        utils.assert_constraint(param, val, ENV_PARAMS, context="Environment Parameters")

    env_params['FLEET_STATE_IDX'] = FLEET_STATE_IDX

    vehicle_types = [data[key] for key in inputs['VEH_KEYS']]
    fleet, fleet_state = initialize_fleet(vehicle_types = vehicle_types,
                             bases = bases,
                             charge_curve = data['charge_curves'],
                             whmi_lookup = data['whmi_lookup'],
                             start_time = reqs_df.pickup_time.iloc[0],
                             env_params = env_params,
                             clock = sim_clock,
                             vehicle_log_file = vehicle_log_file,
                             vehicle_summary_file = vehicle_summary_file)
    if cfg.VERBOSE: print("{} vehicles initialized".format(len(fleet)), "", sep="\n")

    if cfg.VERBOSE: print("#"*30, "Simulating {}".format(sim_name), "#"*30, "", sep="\n")

    dispatcher = Dispatcher(fleet = fleet,
                            fleet_state = fleet_state,
                            stations = stations,
                            bases = bases,
                            env_params = env_params,
                            clock = sim_clock,
                            failed_requests_log = failed_requests_log_file)

    utils.initialize_log(dispatcher._LOG_COLUMNS, failed_requests_log_file)

    sim_start_time = reqs_df.pickup_time.min()
    sim_end_time = reqs_df.dropoff_time.max()
    sim_time_steps = pd.date_range(sim_start_time, sim_end_time, freq='{}S'.format(cfg.SIMULATION_PERIOD_SECONDS))

    total_iterations = len(sim_time_steps)
    i = 0
    with open('performance.txt', 'a') as f:
        start = time.time()
        for timestep in sim_time_steps:
            i+=1
            if i%100 == 0:
                print("{} of {} iterations completed.".format(i, total_iterations))
            requests = reqs_df[(timestep <= reqs_df.pickup_time) \
                & (reqs_df.pickup_time < (timestep + timedelta(seconds=cfg.SIMULATION_PERIOD_SECONDS)))]
            dispatcher.process_requests(requests)
            for veh in fleet:
                veh.step()
            next(sim_clock)
        end = time.time()
        time_s = end-start
        print(f"Scenario: {scenario_name}, Time: {time_s} seconds", file=f)

    #
    import csv
    # keys = fleet[0].history[0].keys()
    # for veh in fleet:
    #     filename = os.path.join(log_path, f'veh_{veh.ID}_history.csv')
    #     with open(filename, 'w') as f:
    #         writer = csv.DictWriter(f, keys)
    #         writer.writeheader()
    #         writer.writerows(veh.history)
    keys = dispatcher.history[0].keys()
    filename = os.path.join(log_path, 'dispatcher_log.csv')
    with open(filename, 'w') as f:
        writer = csv.DictWriter(f, keys)
        writer.writeheader()
        writer.writerows(dispatcher.history)

    #Calculate summary statistics
    # fleet = dispatcher.get_fleet()
    # reporting.calc_veh_stats(fleet, vehicle_summary_file)
    # reporting.calc_fleet_stats(fleet_summary_file, vehicle_summary_file, reqs_df)
    # reporting.summarize_station_use(stations, bases, station_summary_file)
    #
if __name__ == "__main__":
    #TODO: Fix cached functionality. Current functionality does not cache runs.
    # def clean_scenarios_folder():
    #     files = glob.glob(os.path.join(SCENARIO_PATH, '*'))
    #     print(files)
    #     for f in files:
    #         os.remove(f)
    #
    # if not os.path.isdir(SCENARIO_PATH):
    #     print('creating scenarios folder for input files..')
    #     os.makedirs(SCENARIO_PATH)
    #
    # if not os.listdir(SCENARIO_PATH):
    #     subprocess.run('doit build_input_files', shell=True)
    #
    # if '--cached' in sys.argv:
    #     subprocess.run('doit run_simulation', shell=True)
    # else:
    #     clean_scenarios_folder()
    #     subprocess.run('doit forget', shell=True)
    #     subprocess.run('doit build_input_files', shell=True)
    #     subprocess.run('doit run_simulation', shell=True)
    if not os.path.isdir(cfg.OUT_PATH):
        print('Building base output directory..')
        os.makedirs(cfg.OUT_PATH)

    print('Building simulation output directory..')
    if not os.path.isdir(OUT_PATH):
        os.makedirs(OUT_PATH)
    else:
        shutil.rmtree(OUT_PATH)
        os.makedirs(OUT_PATH)

    scenarios = build_input_files()

    for scenario_name, data in scenarios.items():
        run_simulation(data, scenario_name)
