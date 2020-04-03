import numpy as np
import pandas as pd

from hive.util.typealiases import SimTime


class BaseTarget:
    def __init__(self):
        df = pd.read_csv('temp_base_target.csv')
        self.target_lookup = pd.Series(index=df.seconds.values, data=df.num_vehs_charging.values)

    def get_target(self, sim_time: SimTime) -> int:
        if sim_time in self.target_lookup:
            return self.target_lookup[sim_time]
        else:
            self.target_lookup.at[sim_time] = np.nan
            self.target_lookup = self.target_lookup.sort_index().interpolate(method="index")
