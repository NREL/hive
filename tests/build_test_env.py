import sys
import os
import random
import numpy as np

sys.path.append('..')
from run import load_scenario, build_simulation_env
import config

#TODO: Think about more robust way to load inputs for testing.
LIB_PATH = os.path.join('..', 'inputs', 'library')
SCENARIO_PATH = os.path.join('..', 'inputs', 'scenarios')
STATIC_PATH = os.path.join(LIB_PATH, '.static')

TEST_SCENARIO = os.path.join(SCENARIO_PATH, 'aus-test.yaml')

def setup_env():
    print("Building test simulation environment..")
    random.seed(config.RANDOM_SEED)
    np.random.seed(config.RANDOM_SEED)

    scenario_name, data = load_scenario(TEST_SCENARIO)

    SIM_ENV = build_simulation_env(data)

    return SIM_ENV
