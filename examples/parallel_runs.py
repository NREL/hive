import sys
sys.path.append('..')

from hive.helpers import load_scenario
from hive.utils import name
from hive.simulationengine import SimulationEngine

scenario_list = ['api-demo.yaml', 'api-demo2.yaml']

out_path = '../outputs'

def run_scenario(scenario_file):
    input_data = load_scenario(scenario_file)

    sim_eng = SimulationEngine(input_data, out_path)
    sim_eng.run_simulation(name(scenario_file))

from multiprocessing import Pool

NUM_CORES = 2

with Pool(NUM_CORES) as p:
    p.map(run_scenario, scenario_list)
