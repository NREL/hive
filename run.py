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

import config as cfg

SCENARIO_PATH = os.path.join(cfg.IN_PATH, '.scenarios')
OUT_PATH = os.path.join(cfg.OUT_PATH, cfg.SIMULATION_NAME.replace(" ", "_"))

from hive import preprocess as pp
from hive import tripenergy as nrg
from hive import charging as chrg
from hive.vehicle import Vehicle

def build_output_dir(scenario_name):
    scenario_output = os.path.join(OUT_PATH, scenario_name)
    if not os.path.isdir(scenario_output):
        os.makedirs(scenario_output)
        os.makedirs(os.path.join(scenario_output, 'logs'))
        os.makedirs(os.path.join(scenario_output, 'summaries'))


def run_simulation(infile, sim_name):
    vehicle_log_file = os.path.join(OUT_PATH, sim_name, 'logs', 'vehicle_log.csv')
    station_log_file = os.path.join(OUT_PATH, sim_name, 'logs', 'station_log.csv')

    if cfg.VERBOSE: print("Reading input files..")
    inputs = pd.read_hdf(infile, key="main")

    if cfg.VERBOSE: print("Building scenario output directory..")
    build_output_dir(inputs.SCENARIO_NAME.strip().replace(" ", "_"))

    charge_curves = pd.read_hdf(infile, key="charge_curves")

    if cfg.VERBOSE: print("Initializing vehicle fleet..")
    veh_keys = inputs['VEH_KEYS']
    veh_fleet = []
    for key in veh_keys:
        veh_type = pd.read_hdf(infile, key=key)
        charge_template = chrg.construct_temporal_charge_template(
                                                    charge_curves,
                                                    veh_type.BATTERY_CAPACITY,
                                                    veh_type.CHARGE_ACCEPTANCE,
                                                    )
        whmi_lookup = nrg.create_scaled_whmi(
                                    pd.read_hdf(infile, key="whmi_lookup"),
                                    veh_type.EFFICIENCY,
                                    )
        veh_env_params = {
            'MAX_DISPATCH_MILES': inputs.MAX_DISPATCH_MILES,
            'MIN_ALLOWED_SOC': inputs.MIN_ALLOWED_SOC,
        }
        for i in range(0, veh_type.NUM_VEHICLES):
            veh = Vehicle(
                        veh_id = i,
                        name = veh_type.VEHICLE_NAME,
                        type = veh_type.VEHICLE_TYPE,
                        battery_capacity = veh_type.BATTERY_CAPACITY,
                        initial_soc = np.random.uniform(0.2, 1.0),
                        whmi_lookup = whmi_lookup,
                        charge_template = charge_template,
                        logfile = vehicle_log_file,
                        environment_params = veh_env_params,
                        )
            veh_fleet.append(veh)


    random.seed(123)
    random.shuffle(veh_fleet)

    charge_network = pd.read_hdf(infile, key="charge_network")

    random.seed(22) #seed for pax distr sampling
    today = datetime.now()
    date = "{0}-{1}-{2}".format(today.month, today.day, today.year)

    print("#"*30)
    print("Starting Simulation")
    print("#"*30)
    print()

    print("Processing requests")
    #Combine requests files, add pax count if not exists
    reqs_df = pp.load_requests(cfg.REQUEST_PATH)
    print("loaded {} requests".format(len(reqs_df)))

    #Filter requests where distance < 0.05 miles
    reqs_df = pp.filter_short_trips(reqs_df, min_miles=0.05)
    print("filtered requests violating min distance req, {} remain".format(len(reqs_df)))

    #Filter requests where pickup/dropoff location outside operating area
    reqs_df = pp.filter_requests_outside_oper_area(reqs_df, cfg.OPERATING_AREA_PATH)
    print("filtered requests outside of operating area, {} remain".format(len(reqs_df)))

    #Pool requests - from hive.pool, module for various pooling types - o/d, dynamic, n/a

    #reqs_df.to_csv(cfg.OUT_PATH + sim_name + 'requests/' + requests_filename, index=False)

    #Create output paths -

if __name__ == "__main__":
    if not os.path.isdir(SCENARIO_PATH):
        print('creating scenarios folder for input files..')
        os.makedirs(SCENARIO_PATH)
    if not os.listdir(SCENARIO_PATH):
        subprocess.run('doit build_input_files', shell=True)

    if '--clean' in sys.argv:
        subprocess.run('doit forget', shell=True)

    subprocess.run('doit run_simulation', shell=True)
