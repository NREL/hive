"""
Charging station objects used in the HIVE simulation platform.
"""

from hive.constraints import STATION_PARAMS
from hive.utils import assert_constraint, write_log, initialize_log

import utm

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
    total_energy:
        Total energy supplied for recharging in kWh
    avail_plugs:
        Number of plugs that are unoccupied
    """

    def __init__(
                self,
                station_id,
                latitude,
                longitude,
                plugs,
                plug_type,
                plug_power_kw,
                ):

        self.ID = station_id
        self.LAT = latitude
        self.LON = longitude

        x, y, zone_letter, zone_number = utm.from_latlon(latitude, longitude)

        self.X = x
        self.Y = y
        self.ZONE_NUMBER = zone_number
        self.ZONE_LETTER = zone_letter

        assert_constraint("TOTAL_PLUGS", plugs, STATION_PARAMS, context="Initialize FuelStation")
        self.TOTAL_PLUGS = plugs

        assert_constraint("PLUG_TYPE", plug_type, STATION_PARAMS, context="Initialize FuelStation")
        self.PLUG_TYPE = plug_type

        assert_constraint("PLUG_POWER", plug_power_kw, STATION_PARAMS, context="Initialize FuelStation")
        self.PLUG_POWER_KW = plug_power_kw

        self.avail_plugs = plugs
