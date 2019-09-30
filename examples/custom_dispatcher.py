import numpy as np

import sys
sys.path.append('..')

from hive.helpers import load_scenario
from hive.core import SimulationEngine
from hive.dispatcher import Dispatcher

class SmartDispatcher(Dispatcher):
    def _charge_vehicles(self):
        soc_col = self._ENV['FLEET_STATE_IDX']['soc']
        available_col = self._ENV['FLEET_STATE_IDX']['available']
        active_col = self._ENV['FLEET_STATE_IDX']['active']
        mask = (self._fleet_state[:, soc_col] < self._ENV['LOWER_SOC_THRESH_STATION']) \
            & (self._fleet_state[:,available_col] == 1) & (self._fleet_state[:, active_col] == 1)
        veh_ids = np.argwhere(mask)

        for veh_id in veh_ids:
            vehicle = self._fleet[veh_id[0]]
            station = self._find_closest_plug(vehicle)
            route_summary = self._route_engine.route(
                                        vehicle.x,
                                        vehicle.y,
                                        station.X,
                                        station.Y,
                                        'Moving to Station',
                                        )
            route = route_summary['route']
            vehicle.cmd_charge(station, route)

        # Implement custom charge logic. For example:
        #
        # soc = self._fleet_state[:, soc_col]
        # top_10_soc = np.argsort(soc)[:-10]
        # for veh_id in top_10_soc:
        #     vehicle = self._fleet[veh_id[0]]
        #     vehicle.cmd_unplug()

    def _check_idle_vehicles(self):
        idle_min_col = self._ENV['FLEET_STATE_IDX']['idle_min']
        idle_mask = self._fleet_state[:, idle_min_col] >= self._ENV['MAX_ALLOWABLE_IDLE_MINUTES']
        veh_ids = np.argwhere(idle_mask)

        for veh_id in veh_ids:
            vehicle = self._fleet[veh_id[0]]
            base = self._find_closest_plug(vehicle, type='base')
            route_summary = self._route_engine.route(vehicle.x, vehicle.y, base.X, base.Y, 'Moving to Base')
            route = route_summary['route']
            vehicle.cmd_return_to_base(base, route)


# Replace with your own scenario
scenario_path = 'api-demo.yaml'

# This is where the simulation will write outputs
out_path = '../outputs'

input_data = load_scenario(scenario_path)

sim_eng = SimulationEngine(input_data, out_path = out_path, dispatcher = SmartDispatcher())

sim_eng.run_simulation('test_custom_dispatcher')
