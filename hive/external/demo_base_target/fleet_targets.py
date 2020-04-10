import os

import numpy as np
import pandas as pd

from hive.util.typealiases import SimTime

THIS_DIR = os.path.dirname(os.path.realpath(__file__))


class FleetTarget:
    def __init__(self):
        df = pd.read_csv(os.path.join(THIS_DIR, 'fleet_targets.csv'))
        self.base_target = pd.Series(index=df.seconds.values, data=df.base_charging.values)
        self.station_target = pd.Series(index=df.seconds.values, data=df.station_charging.values)
        self.active_target = pd.Series(index=df.seconds.values, data=df.field_vehicles.values)

    def get_base_target(self, sim_time: SimTime) -> int:
        if sim_time not in self.base_target:
            self.base_target.at[sim_time] = np.nan
            self.base_target = self.base_target.sort_index().interpolate(method="index")

        return self.base_target[sim_time]
    
    def get_station_target(self, sim_time: SimTime) -> int:
        if sim_time not in self.station_target:
            self.station_target.at[sim_time] = np.nan
            self.station_target = self.station_target.sort_index().interpolate(method="index")

        return self.station_target[sim_time]
    
    def get_active_target(self, sim_time: SimTime) -> int:
        if sim_time not in self.active_target:
            self.active_target.at[sim_time] = np.nan
            self.active_target = self.active_target.sort_index().interpolate(method="index")

        return self.active_target[sim_time]
