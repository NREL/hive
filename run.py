"""
Run hive w/ inputs defined in config.py
"""
import glob
import logging.config
import os
import random

import numpy as np
import yaml

import config as cfg
from hive.helpers import load_scenario
from hive.simulationengine import SimulationEngine
from hive.utils import name

random.seed(cfg.RANDOM_SEED)
np.random.seed(cfg.RANDOM_SEED)
THIS_DIR = os.path.dirname(os.path.realpath(__file__))
SCENARIO_PATH = os.path.join(THIS_DIR, cfg.IN_PATH, 'scenarios')

OUT_PATH = os.path.join(THIS_DIR, cfg.OUT_PATH)

if __name__ == "__main__":

    if not os.path.isdir(OUT_PATH):
        os.makedirs(cfg.OUT_PATH)

    assert len(cfg.SCENARIOS) == len(set(cfg.SCENARIOS)), 'Scenario names must be unique.'

    all_scenarios = glob.glob(os.path.join(SCENARIO_PATH, '*.yaml'))

    if len(all_scenarios) == 0:
        print('Looks like there are no scenarios in your inputs/scenarios folder.')
        print('To generate scenarios, navigate to the inputs directory and run:')
        print('python generate_scenarios.py')

    run_scenarios = [s for s in all_scenarios if name(s) in cfg.SCENARIOS]

    for scenario_file in run_scenarios:
        data = load_scenario(scenario_file)

        simulation_engine = SimulationEngine(data, OUT_PATH)
        simulation_engine.run_simulation(name(scenario_file))
