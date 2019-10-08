import pandas as pd
import os

import sys
sys.path.append('..')

from hive.helpers import load_scenario
from hive.simulationengine import SimulationEngine

# Replace with your own base scenario
scenario_path = 'api-demo.yaml'

# This is where the simulation will write outputs
out_path = '../outputs'

input_data = load_scenario(scenario_path)

sim_eng = SimulationEngine(input_data, out_path = out_path)

fleet_sizes = [100, 200, 400, 800, 1600, 3200, 6400]
target_demand_served = 95 # percent
for size in fleet_sizes:

    # Use the input_data attribute to change the inputs programatically.
    # WARNING: Be sure not to change any of the column names.
    sim_eng.input_data['vehicles'].loc['car_4pax', 'NUM_VEHICLES'] = size

    sim_name = f'fleet_size_{size}'

    # Each call to run_simulation will spawn a new simulation.
    sim_eng.run_simulation(sim_name = sim_name)

    dispatcher_log = os.path.join(out_path, sim_name, 'logs', 'dispatcher', 'dispatcher.csv')
    dispatcher_df = pd.read_csv(dispatcher_log)

    demand = dispatcher_df.total_requests.sum()
    served = demand - dispatcher_df.dropped_requests.sum()
    demand_served = (served/demand) * 100

    if demand_served > target_demand_served:
        print(f"Fleet size of {size} was able to serve {demand_served}% of demand")
        break
    else:
        print(f"Fleet size of {size} was not able to meet target. Only served {demand_served}% of demand")
