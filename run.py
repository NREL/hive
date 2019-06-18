"""
Run hive w/ inputs defined in config.py
"""
import subprocess
import os
import sys
import random
import shutil
from datetime import datetime
import pandas as pd
import numpy as np
import pickle

import config as cfg

from hive import preprocess as pp
from hive import tripenergy as nrg
from hive import charging as chrg
from hive import utils
from hive import reporting
from hive.initialize import initialize_stations, initialize_bases, initialize_fleet
from hive.vehicle import Vehicle
from hive.dispatcher import Dispatcher


seed = 123
random.seed(seed)
np.random.seed(seed)
THIS_DIR = os.path.dirname(os.path.realpath(__file__))
SCENARIO_PATH = os.path.join(THIS_DIR, cfg.IN_PATH, '.scenarios', cfg.SIMULATION_NAME.replace(" ", "_"))
OUT_PATH = os.path.join(THIS_DIR, cfg.OUT_PATH, cfg.SIMULATION_NAME.replace(" ", "_"))

def run_simulation(infile, sim_name):
    with open(infile, 'rb') as f:
        data = pickle.load(f)
    vehicle_log_file = os.path.join(OUT_PATH, sim_name, 'logs', 'vehicle_log.csv')
    station_log_file = os.path.join(OUT_PATH, sim_name, 'logs', 'station_log.csv')
    base_log_file = os.path.join(OUT_PATH, sim_name, 'logs', 'base_log.csv')

    vehicle_summary_file = os.path.join(OUT_PATH, sim_name, 'summaries', 'vehicle_summary.csv')
    fleet_summary_file = os.path.join(OUT_PATH, sim_name, 'summaries', 'fleet_summary.txt')


    if cfg.VERBOSE: print("", "#"*30, "Preparing {}".format(sim_name), "#"*30, "", sep="\n")

    if cfg.VERBOSE: print("Reading input files..", "", sep="\n")
    inputs = data['main']

    if cfg.VERBOSE: print("Building scenario output directory..", "", sep="\n")
    utils.build_output_dir(sim_name, OUT_PATH)

    #Load requests
    if cfg.VERBOSE: print("Processing requests..")
    reqs_df = data['requests']
    if cfg.VERBOSE: print("{} requests loaded".format(len(reqs_df)))

    #Filter requests where distance < 0.05 miles
    reqs_df = pp.filter_short_trips(reqs_df, min_miles=0.05)
    if cfg.VERBOSE: print("filtered requests violating min distance req, {} remain".format(len(reqs_df)))

    #Filter requests where pickup/dropoff location outside operating area
    shp_file = inputs['OPERATING_AREA_SHP']
    oa_filepath = os.path.join(cfg.IN_PATH, 'operating_area', shp_file)
    reqs_df = pp.filter_requests_outside_oper_area(reqs_df, oa_filepath)
    if cfg.VERBOSE: print("filtered requests outside of operating area, {} remain".format(len(reqs_df)), "", sep="\n")

    #Calculate network scaling factor & average dispatch speed
    RN_SCALING_FACTOR = pp.calculate_road_vmt_scaling_factor(reqs_df)
    DISPATCH_MPH = pp.calculate_average_driving_speed(reqs_df)

    #TODO: Pool requests - from hive.pool, module for various pooling types - o/d, dynamic, n/a
    #TODO: reqs_df.to_csv(cfg.OUT_PATH + sim_name + 'requests/' + requests_filename, index=False)

    #Load charging network
    if cfg.VERBOSE: print("Loading charge network..")
    stations = initialize_stations(data['charge_stations'], station_log_file)
    bases, base_power_lookup = initialize_bases(data['veh_bases'], base_log_file)
    if cfg.VERBOSE: print("loaded {0} stations & {1} bases".format(len(stations), len(bases)), "", sep="\n")

    #Initialize vehicle fleet
    if cfg.VERBOSE: print("Initializing vehicle fleet..", "", sep="\n")
    charge_curve = data['charge_curves']
    fleet_env_params = {
        'MAX_DISPATCH_MILES': inputs.MAX_DISPATCH_MILES,
        'MIN_ALLOWED_SOC': inputs.MIN_ALLOWED_SOC,
        'RN_SCALING_FACTOR': RN_SCALING_FACTOR,
        'DISPATCH_MPH': DISPATCH_MPH,
    }

    vehicle_types = [data[key] for key in inputs['VEH_KEYS']]
    fleet = initialize_fleet(vehicle_types = vehicle_types,
                             bases = bases,
                             charge_curve = data['charge_curves'],
                             whmi_lookup = data['whmi_lookup'],
                             env_params = fleet_env_params,
                             vehicle_log_file = vehicle_log_file,
                             vehicle_summary_file = vehicle_summary_file)
    if cfg.VERBOSE: print("{} vehicles initialized".format(len(fleet)), "", sep="\n")

    if cfg.VERBOSE: print("#"*30, "Simulating {}".format(sim_name), "#"*30, "", sep="\n")

    dispatcher = Dispatcher(fleet = fleet,
                            stations = stations,
                            bases = bases,
                            base_power_lookup = base_power_lookup)

    for req in reqs_df.itertuples(name='Request'):
        request = {'pickup_time': req[0],
                   'dropoff_time': req[1],
                   'distance_miles': req[2],
                   'pickup_lat': req[3],
                   'pickup_lon': req[4],
                   'dropoff_lat': req[5],
                   'dropoff_lon': req[6],
                   'passengers': req[7]}
        dispatcher.process_requests(request) ## <--STATUS -bb

    #Calculate summary statistics
    reporting.calc_veh_stats(fleet, vehicle_summary_file)
    reporting.calc_fleet_stats(fleet_summary_file, vehicle_summary_file, reqs_df)



if __name__ == "__main__":
    if not os.path.isdir(SCENARIO_PATH):
        print('creating scenarios folder for input files..')
        os.makedirs(SCENARIO_PATH)

    if not os.listdir(SCENARIO_PATH):
        subprocess.run('doit build_input_files', shell=True)

    if '--clean' in sys.argv:
        subprocess.run('doit forget', shell=True)

    subprocess.run('doit run_simulation', shell=True)
