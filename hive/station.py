"""
Charging station object for mist algorithm
"""

import csv

from hive.constraints import STATION_PARAMS
from hive.utils import assert_constraint

class FuelStation:
    """
    Base class for electric vehicle charging station.

    Inputs
    ------
    station_id : int
        Identifer assigned to FuelStation object
    latitude : float
        Latitude of station location
    longitude: float
        Longitude of station location
    plugs: int
        Number of plugs at location
    plug_type: str
        Plug type - AC or DC
    plug_power: float
        Plug power in kW
    logfile: str
        Path to fuel station log file

    Attributes
     ----------
    charge_cnt:
        Number of charge events
    instantaneous_pwr:
        Instantaneous load in kW
    peak_pwr:
        Peak load in kW
    total_energy:
        Total energy supplied for recharging in kWh
    avail_plugs:
        Number of plugs that are unoccupied
    """

    _STATS = [
        'charge_cnt',
        'instantaneous_pwr',
        'peak_pwr',
        'total_energy'
        ]

    def __init__(
                self,
                station_id,
                latitude,
                longitude,
                plugs,
                plug_type,
                plug_power,
                logfile
                ):

        self.ID = station_id
        self.LAT = latitude
        self.LON = longitude

        assert_constraint("TOTAL_PLUGS", plugs, STATION_PARAMS, context="Initialize FuelStation")
        self.TOTAL_PLUGS = plugs

        assert_constraint("PLUG_TYPE", plug_type, STATION_PARAMS, context="Initialize FuelStation")
        self.PLUG_TYPE = plug_type

        assert_constraint("PLUG_POWER", plug_power, STATION_PARAMS, context="Initialize FuelStation")
        self.PLUG_POWER = plug_power

        self.avail_plugs = plugs

        self._log = logfile
        self.stats = dict()
        for stat in self._STATS:
            self.stats[stat] = 0

    def add_charge_event(self, veh, start_time, end_time, soc_i, soc_f):
        #TODO: Update
        self.stats['charge_cnt'] += 1
        with open(self._log, 'a') as f:
            writer = csv.writer(f)
            writer.writerow([self.ID, veh_id, start_time, end_time, soc_i, soc_f])