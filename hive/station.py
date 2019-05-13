"""
Charging station object for mist algorithm
"""

import csv

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

    STATS = [
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

        self.id = station_id
        self.lat = latitude
        self.lon = longitude
        self.total_plugs = plugs
        self.avail_plugs = plugs
        self.type = plug_type
        self.plug_power = plug_power

        self._log = logfile
        self._stats = dict()
        for stat in self.STATS:
            self._stats[stat] = 0

    def add_charge_event(self, veh, start_time, end_time, soc_i, soc_f):
        #TODO: Update
        self._stats['charge_cnt'] += 1
        with open(self._log, 'a') as f:
            writer = csv.writer(f)
            writer.writerow([self.id, veh_id, start_time, end_time, soc_i, soc_f])
