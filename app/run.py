from datetime import datetime

import yaml
import sys
import csv
import os
import time

sys.path.append('..')

from hive.config import *
from hive.runner.local_simulation_runner import LocalSimulationRunner
from hive.runner.environment import Environment
from hive.reporting.detailed_reporter import DetailedReporter
from hive.dispatcher.greedy_dispatcher import GreedyDispatcher
from hive.state.simulation_state_ops import initial_simulation_state
from hive.state.update import UpdateRequestsFromFile, CancelRequests, StepSimulation

RESOURCES = os.path.join('..', 'hive', 'resources')

if len(sys.argv) == 1:
    raise ImportError("please specify a scenario file to run.")

scenario_file = sys.argv[1]
with open(scenario_file, 'r') as f:
    config_builder = yaml.safe_load(f)

config = HiveConfig.build(config_builder)

run_name = config.sim.sim_name + '_' + datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
sim_output_dir = os.path.join(config.io.working_directory, run_name)
if not os.path.isdir(sim_output_dir):
    os.makedirs(sim_output_dir)

env = Environment(config=config)
dispatcher = GreedyDispatcher()

initial_sim, sim_state_errors = initial_simulation_state(
    road_network=road_network,
    vehicles=vehicles,
    stations=stations,
    bases=bases,
    sim_timestep_duration_seconds=config.sim.timestep_duration_seconds,
    sim_h3_search_resolution=config.sim.sim_h3_search_resolution,
)

if sim_state_errors:
    raise Exception(sim_state_errors)

# TODO: move this lower and make it ordered.
update_functions = (UpdateRequestsFromFile.build(requests_file), CancelRequests(), StepSimulation(dispatcher))

runner = LocalSimulationRunner(env=env)
reporter = DetailedReporter(config.io, sim_output_dir)
start = time.time()
sim_result = runner.run(
    initial_simulation_state=initial_sim,
    update_functions=update_functions,
    reporter=reporter,
)
end = time.time()
print(f'done! time elapsed: {round(end - start, 2)} seconds')
