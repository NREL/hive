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
from hive.utils import info
from hive.core import SimulationEngine

random.seed(cfg.RANDOM_SEED)
np.random.seed(cfg.RANDOM_SEED)
THIS_DIR = os.path.dirname(os.path.realpath(__file__))
SCENARIO_PATH = os.path.join(THIS_DIR, cfg.IN_PATH, 'scenarios')

OUT_PATH = os.path.join(THIS_DIR, cfg.OUT_PATH)

def name(path):
    return os.path.splitext(os.path.basename(path))[0]

def load_scenario(scenario_file):

    info(f"Preparing {name(scenario_file)}")

    scenario_name = name(scenario_file)
    with open(scenario_file, 'r') as f:
        info('Loading scenario file..')
        yaml_data = yaml.safe_load(f)

        data = {}

        filepaths = yaml_data['filepaths']

        data['requests'] = pp.load_requests(filepaths['requests_file_path'],
                                            verbose = cfg.VERBOSE,
                                            )
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

        #Configuartion
        data['SIMULATION_PERIOD_SECONDS'] = cfg.SIMULATION_PERIOD_SECONDS
        data['USE_OSRM'] = cfg.USE_OSRM
        data['OSRM_SERVER'] = cfg.OSRM_SERVER


    return data

if __name__ == "__main__":
    if not os.path.isdir(OUT_PATH):
        info('Building base output directory..')
        os.makedirs(cfg.OUT_PATH)

    assert len(cfg.SCENARIOS) == len(set(cfg.SCENARIOS)), 'Scenario names must be unique.'

    all_scenarios = glob.glob(os.path.join(SCENARIO_PATH, '*.yaml'))

    if len(all_scenarios) == 0:
        info('Looks like there are no scenarios in your inputs/scenarios folder.')
        info('To generate scenarios, navigate to the inputs directory and run:')
        info('python generate_scenarios.py')

    run_scenarios = [s for s in all_scenarios if name(s) in cfg.SCENARIOS]

    for scenario_file in run_scenarios:
        data = load_scenario(scenario_file)
        simulation_engine = SimulationEngine(data)
        simulation_engine.run_simulation(name(scenario_file), OUT_PATH)
