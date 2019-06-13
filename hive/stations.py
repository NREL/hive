"""
Charging station object for mist algorithm
"""

import csv

from hive.constraints import STATION_PARAMS
from hive.utils import assert_constraint, write_log, initialize_log

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

    _LOG_COLUMNS = [
        'station_id',
        'vehicle_id',
        'start_time',
        'end_time',
        'soc_i',
        'soc_f',
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

        self._logfile = logfile
        initialize_log(self._LOG_COLUMNS, self._logfile)

        self.stats = dict()
        for stat in self._STATS:
            self.stats[stat] = 0

    def add_charge_event(self, veh, start_time, end_time, soc_i, soc_f):
        #TODO: Update
        self.stats['charge_cnt'] += 1
        write_log({
            'station_id': self.ID,
            'vehicle_id': veh.ID,
            'start_time': start_time,
            'end_time': end_time,
            'soc_i': soc_i,
            'soc_f': soc_f,
            },
            self._LOG_COLUMNS,
            self._logfile)

    
    class VehicleDepot:
        """
        Base class for fleet vehicle depot. Vehicle depots are locations that 
        inactive vehicles return to when they are not serving demand to recharge for
        the next peak period.

        Inputs
        ------
        depot_id : int
            Identifer assigned to VehicleDepot object
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
            Path to depot log file

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

    _LOG_COLUMNS = [
        'depot_id',
        'vehicle_id',
        'start_time',
        'end_time',
        'soc_i',
        'soc_f',
        ]

    def __init__(
                self,
                depot_id,
                latitude,
                longitude,
                plugs,
                plug_type,
                plug_power,
                logfile
                ):

        self.ID = depot_id
        self.LAT = latitude
        self.LON = longitude

        assert_constraint("TOTAL_PLUGS", plugs, STATION_PARAMS, context="Initialize FuelStation")
        self.TOTAL_PLUGS = plugs

        assert_constraint("PLUG_TYPE", plug_type, STATION_PARAMS, context="Initialize FuelStation")
        self.PLUG_TYPE = plug_type

        assert_constraint("PLUG_POWER", plug_power, STATION_PARAMS, context="Initialize FuelStation")
        self.PLUG_POWER = plug_power

        self.avail_plugs = plugs

        self._logfile = logfile
        initialize_log(self._LOG_COLUMNS, self._logfile)

        self.stats = dict()
        for stat in self._STATS:
            self.stats[stat] = 0

    def add_charge_event(self, veh, start_time, end_time, soc_i, soc_f):
        #TODO: Update
        self.stats['charge_cnt'] += 1
        write_log({
            'station_id': self.ID,
            'vehicle_id': veh.ID,
            'start_time': start_time,
            'end_time': end_time,
            'soc_i': soc_i,
            'soc_f': soc_f,
            },
            self._LOG_COLUMNS,
            self._logfile)
