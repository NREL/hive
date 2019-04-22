"""
Run hive w/ inputs defined in config.py
"""
import subprocess
import os
import sys
import random
from datetime import datetime
import pandas as pd
import numpy as np

import config as cfg

SCENARIO_PATH = os.path.join(cfg.IN_PATH, '.scenarios')
LIB_PATH = os.path.join(cfg.IN_PATH, '.lib')

WHMI_LOOKUP_FILE = os.path.join(LIB_PATH, 'wh_mi_lookup.csv')

from hive import preprocess as pp
from hive import tripenergy as nrg
from hive import charging as chrg
from hive.vehicle import Vehicle

def build_output_dir(scenario_name):
    pass

def run_simulation(infile, outfile):
    if cfg.VERBOSE: print("Reading input files..")
    inputs = pd.read_hdf(infile, key="main")

    veh_keys = inputs['VEH_KEYS']

    veh_types = []
    for key in veh_keys:
        veh = pd.read_hdf(infile, key=key)
        veh_types.append(veh)


    charge_curves = pd.read_hdf(infile, key="charge_curves")

    if cfg.VERBOSE: print("Initializing vehicle fleet..")
    veh_fleet = []
    for veh_type in veh_types:
        charge_template = chrg.construct_temporal_charge_template(
                                                        charge_curves,
                                                        veh_type.BATTERY_CAPACITY,
                                                        veh_type.CHARGE_ACCEPTANCE,
                                                        )
        whmi_lookup = nrg.create_scaled_whmi(
                                    pd.read_csv(WHMI_LOOKUP_FILE),
                                    veh_type.EFFICIENCY,
                                    )
        for i in range(0, veh_type.NUM_VEHICLES):
            veh = Vehicle(
                        veh_id = i,
                        battery_capacity = veh_type.BATTERY_CAPACITY,
                        initial_soc = np.random.uniform(0.2, 1.0),
                        whmi_lookup = whmi_lookup,
                        charge_template = charge_template,
                        logfile = "placeholder.log"
                        )

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

    reqs_df.to_hdf(outfile, key="requests")
    #Create output paths -

if __name__ == "__main__":
    if not os.path.isdir(SCENARIO_PATH):
        print('creating scenarios folder for input files..')
        subprocess.run('mkdir {}'.format(SCENARIO_PATH), shell=True)
    if not os.listdir(SCENARIO_PATH):
        subprocess.run('doit build_input_files', shell=True)

    if '--clean' in sys.argv:
        subprocess.run('doit forget', shell=True)

    subprocess.run('doit run_simulation', shell=True)
