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
import logging
import logging.config


from hive.utils import name
from hive.SimulationEngine import SimulationEngine
from hive.helpers import load_scenario


random.seed(cfg.RANDOM_SEED)
np.random.seed(cfg.RANDOM_SEED)
THIS_DIR = os.path.dirname(os.path.realpath(__file__))
SCENARIO_PATH = os.path.join(THIS_DIR, cfg.IN_PATH, 'scenarios')

OUT_PATH = os.path.join(THIS_DIR, cfg.OUT_PATH)

if __name__ == "__main__":

    # apply logging configuration for all hive modules
    if os.path.isfile("logging.yml"):
        with open("logging.yml", "rt") as file:
            logging_config = yaml.safe_load(file.read())
        logging.config.dictConfig(logging_config)
    log = logging.getLogger(__name__)

    if not os.path.isdir(OUT_PATH):
        log.info('Building base output directory..')
        os.makedirs(cfg.OUT_PATH)

    assert len(cfg.SCENARIOS) == len(set(cfg.SCENARIOS)), 'Scenario names must be unique.'

    all_scenarios = glob.glob(os.path.join(SCENARIO_PATH, '*.yaml'))

    if len(all_scenarios) == 0:
        log.info('Looks like there are no scenarios in your inputs/scenarios folder.')
        log.info('To generate scenarios, navigate to the inputs directory and run:')
        log.info('python generate_scenarios.py')

    run_scenarios = [s for s in all_scenarios if name(s) in cfg.SCENARIOS]

    for scenario_file in run_scenarios:
        log.info(f'Preparing {name(scenario_file)}..')
        data = load_scenario(scenario_file)
        simulation_engine = SimulationEngine(data, OUT_PATH)
        simulation_engine.run_simulation(name(scenario_file))
