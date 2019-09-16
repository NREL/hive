import sys
import os
import random
import numpy as np

sys.path.append('..')
from hive.core import SimulationEngine
from hive.helpers import load_scenario
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

    data = load_scenario(TEST_SCENARIO)

    sim_eng = SimulationEngine(data)

    sim_eng._build_simulation_env()

    return sim_eng._SIM_ENV

def load_test_scenario():
    data = load_scenario(TEST_SCENARIO)
    return data
