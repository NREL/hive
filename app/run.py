import os
import sys
import time
from datetime import datetime

import yaml
from pkg_resources import resource_filename

sys.path.append('..')

from hive.config import *
from hive.dispatcher.greedy_dispatcher import GreedyDispatcher
from hive.reporting.detailed_reporter import DetailedReporter
from hive.runner.local_simulation_runner import LocalSimulationRunner
from hive.state.initialize_simulation import initialize_simulation
from hive.state.update import UpdateRequests, CancelRequests, StepSimulation

if len(sys.argv) == 1:
    raise ImportError("please specify a scenario file to run.")

scenario_file = sys.argv[1]
with open(scenario_file, 'r') as f:
    config_builder = yaml.safe_load(f)

config = HiveConfig.build(config_builder)
if isinstance(config, Exception):
    raise config

run_name = config.sim.sim_name + '_' + datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
sim_output_dir = os.path.join(config.io.working_directory, run_name)
if not os.path.isdir(sim_output_dir):
    os.makedirs(sim_output_dir)

dispatcher = GreedyDispatcher()

simulation_state, environment = initialize_simulation(config)

requests_file = resource_filename("hive.resources.requests", config.io.requests_file)
rate_structure_file = resource_filename("hive.resources.service_prices", config.io.rate_structure_file)

# TODO: move this lower and make it ordered.
update_functions = (
    UpdateRequests.build(requests_file, rate_structure_file),
    CancelRequests(),
    StepSimulation(dispatcher),
)

runner = LocalSimulationRunner(env=environment)
reporter = DetailedReporter(config.io, sim_output_dir)
start = time.time()
sim_result = runner.run(
    initial_simulation_state=simulation_state,
    update_functions=update_functions,
    reporter=reporter,
)
end = time.time()
print(f'done! time elapsed: {round(end - start, 2)} seconds')
