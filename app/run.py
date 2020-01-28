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
from hive.model.roadnetwork.haversine_roadnetwork import HaversineRoadNetwork
from hive.model import Vehicle, Base, Station
from hive.model.energy.powertrain import build_powertrain
from hive.model.energy.powercurve import build_powercurve

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
road_network = HaversineRoadNetwork(config.sim.sim_h3_resolution)

vehicles_file = os.path.join(RESOURCES, 'vehicles', config.io.vehicles_file)
requests_file = os.path.join(RESOURCES, 'requests', config.io.requests_file)
bases_file = os.path.join(RESOURCES, 'bases', config.io.bases_file)
stations_file = os.path.join(RESOURCES, 'stations', config.io.stations_file)

build_errors = []

with open(vehicles_file, 'r', encoding='utf-8-sig') as vf:
    builder = []
    reader = csv.DictReader(vf)
    for row in reader:
        try:
            vehicle = Vehicle.from_row(row, road_network)
            builder.append(vehicle)
        except IOError as err:
            build_errors.append(err)
        try:
            if row['powertrain_id'] not in env.powertrains:
                powertrain = build_powertrain(row['powertrain_id'])
                env = env.add_powertrain(powertrain)
        except IOError as err:
            build_errors.append(err)
        try:
            if row['powercurve_id'] not in env.powercurves:
                powercurve = build_powercurve(row['powercurve_id'])
                env = env.add_powercurve(powercurve)
        except IOError as err:
            build_errors.append(err)

    vehicles = tuple(builder)

with open(bases_file, 'r', encoding='utf-8-sig') as bf:
    builder = []
    reader = csv.DictReader(bf)
    for row in reader:
        try:
            base = Base.from_row(row, config.sim.sim_h3_resolution)
            builder.append(base)
        except IOError as err:
            build_errors.append(err)

    bases = tuple(builder)

with open(stations_file, 'r', encoding='utf-8-sig') as sf:
    builder = {}
    reader = csv.DictReader(sf)
    for row in reader:
        try:
            station = Station.from_row(row, builder, config.sim.sim_h3_resolution)
            builder[station.id] = station
        except IOError as err:
            build_errors.append(err)

    stations = tuple(builder.values())

if build_errors:
    raise Exception(build_errors)

initial_sim, sim_state_errors = initial_simulation_state(
    road_network=road_network,
    vehicles=vehicles,
    stations=stations,
    bases=bases,
    start_time=config.sim.start_time,
    sim_timestep_duration_seconds=config.sim.timestep_duration_seconds,
    sim_h3_search_resolution=config.sim.sim_h3_search_resolution,
)

if sim_state_errors:
    raise Exception(sim_state_errors)

# TODO: move this lower and make it ordered.
update_functions = (UpdateRequestsFromFile.build(requests_file, env), CancelRequests(), StepSimulation(dispatcher))

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
