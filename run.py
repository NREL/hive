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

from hive.utils import info, name
from hive.core import SimulationEngine
from hive.helpers import load_scenario

random.seed(cfg.RANDOM_SEED)
np.random.seed(cfg.RANDOM_SEED)
THIS_DIR = os.path.dirname(os.path.realpath(__file__))
SCENARIO_PATH = os.path.join(THIS_DIR, cfg.IN_PATH, 'scenarios')

OUT_PATH = os.path.join(THIS_DIR, cfg.OUT_PATH)

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
        info(f'Preparing {name(scenario_file)}..')
        data = load_scenario(scenario_file)
        simulation_engine = SimulationEngine(data, OUT_PATH)
        simulation_engine.run_simulation(name(scenario_file))
