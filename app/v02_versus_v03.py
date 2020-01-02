import sys
sys.path.append('..')

from hive.config import *
from hive.runner.local_simulation_runner import LocalSimulationRunner
from hive.runner.environment import Environment
from hive.reporting.detailed_reporter import DetailedReporter
from hive.dispatcher.greedy_dispatcher import GreedyDispatcher
from hive.state.simulation_state_ops import initial_simulation_state
from hive.state.update import UpdateRequestsFromString, CancelRequests
from hive.model.roadnetwork.haversine_roadnetwork import HaversineRoadNetwork
from hive.util.units import unit

from app.denver_test_inputs import (
    vehicles,
    stations,
    bases,
    powertrains,
    powercurves,
    requests,
)

config_builder = {
    "sim": {
        'timestep_duration_seconds': 60*unit.seconds,
    },
    "io": {
        'working_directory': 'outputs',
        'vehicles_file': '',
        'requests_file': '',
    }
}
config = HiveConfig.build(config_builder)
env = Environment(config=config)
runner = LocalSimulationRunner(env=env)
reporter = DetailedReporter(config.io)
dispatcher = GreedyDispatcher()

initial_sim, errors = initial_simulation_state(
    road_network=HaversineRoadNetwork(),
    vehicles=vehicles,
    stations=stations,
    bases=bases,
    powertrains=powertrains,
    powercurves=powercurves,
    sim_timestep_duration_seconds=config.sim.timestep_duration_seconds,
    sim_h3_search_resolution=7
)

print(errors)

update_functions = (CancelRequests(), UpdateRequestsFromString(requests))

if __name__ == "__main__":

    sim_result = runner.run(
        initial_simulation_state=initial_sim,
        initial_dispatcher=dispatcher,
        update_functions=update_functions,
        reporter=reporter,
    )

