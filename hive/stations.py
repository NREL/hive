"""
Charging station objects used in the HIVE simulation platform.
"""

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
    total_energy:
        Total energy supplied for recharging in kWh
    avail_plugs:
        Number of plugs that are unoccupied
    """

    _STATS = [
        'charge_cnt',
        'total_energy_kwh'
        ]

    _LOG_COLUMNS = [
        'id',
        'plug_type',
        'plug_power_kw'
        'vehicle_id',
        'max_veh_acceptance_kw',
        'start_time',
        'end_time',
        'soc_i',
        'soc_f',
        'total_energy_kwh'
        ]

    def __init__(
                self,
                station_id,
                latitude,
                longitude,
                plugs,
                plug_type,
                plug_power_kw,
                logfile
                ):

        self.ID = station_id
        self.LAT = latitude
        self.LON = longitude

        assert_constraint("TOTAL_PLUGS", plugs, STATION_PARAMS, context="Initialize FuelStation")
        self.TOTAL_PLUGS = plugs

        assert_constraint("PLUG_TYPE", plug_type, STATION_PARAMS, context="Initialize FuelStation")
        self.PLUG_TYPE = plug_type

        assert_constraint("PLUG_POWER", plug_power_kw, STATION_PARAMS, context="Initialize FuelStation")
        self.PLUG_POWER_KW = plug_power_kw

        self.avail_plugs = plugs

        self._logfile = logfile

        self.stats = dict()
        for stat in self._STATS:
            self.stats[stat] = 0

    def add_charge_event(self, veh, start_time, end_time, soc_i, soc_f, total_energy_kwh):

        """
        Updates FuelStation tracking and logging w/ a new charge event.

        Updates FuelStation & logging with energy consumed (total_energy_kwh)
        by charge event. Logs start & end time of charging event in addition to
        initial & final vehicle SOC & plug power & type to reconstruct detailed
        demand-side electical load curves.

        Parameters
        ----------
        veh: hive.vehicle.Vehicle
            Vehicle that completed the recharge event
        start_time: datetime.datetime
            Datetime that charge_event began
        end_time: datetime.datetime
            Datetime that charge_event concluded
        soc_i: double precision
            Initial fractional state of charge of vehicle's battery
        soc_f: double precision
            Final fractional state of charge of vehicle's battery
        total_energy_kwh: double precision
            Energy (in kWh) consumed during charge event

        Returns
        -------
        None
        """

        write_log({
            'id': self.ID,
            'plug_type': self.PLUG_TYPE,
            'plug_power_kw': self.PLUG_POWER_KW,
            'vehicle_id': veh.ID,
            'max_veh_acceptance_kw': veh.MAX_CHARGE_ACCEPTANCE_KW,
            'start_time': start_time,
            'end_time': end_time,
            'soc_i': soc_i,
            'soc_f': soc_f,
            'total_energy_kwh': total_energy_kwh
            },
            self._LOG_COLUMNS,
            self._logfile)

        self.avail_plugs-=1
        self.stats['charge_cnt']+=1
        self.stats['total_energy_kwh']+=total_energy_kwh


class VehicleBase:
    """
    Base class for fleet vehicle base (home) location. Vehicle bases are
    locations that inactive vehicles return to when they are not serving
    demand to recharge for the next peak period. Vehicles can be assigned
    to a base (home) location or bases can accomodate many inactive vehicles
    (similar to a fleet depot).

    Inputs
    ------
    base_id : int
        Identifer assigned to VehicleBase object
    latitude : float
        Latitude of base location
    longitude: float
        Longitude of base location
    plugs: int
        Number of plugs at location
    plug_type: str
        Plug type - AC or DC
    plug_power: float
        Plug power in kW
    logfile: str
        Path to base log file

    Attributes
    ----------
    charge_cnt:
        Number of charge events
    total_energy:
        Total energy supplied for recharging in kWh
    avail_plugs:
        Number of plugs that are unoccupied
    """

    _STATS = [
        'charge_cnt',
        'total_energy_kwh'
        ]

    _LOG_COLUMNS = [
        'id',
        'plug_type',
        'plug_power_kw',
        'vehicle_id',
        'max_veh_acceptance_kw',
        'start_time',
        'end_time',
        'soc_i',
        'soc_f',
        'total_energy_kwh'
        ]

    def __init__(
                self,
                base_id,
                latitude,
                longitude,
                plugs,
                plug_type,
                plug_power_kw,
                logfile
                ):

        self.ID = base_id
        self.LAT = latitude
        self.LON = longitude

        assert_constraint("TOTAL_PLUGS", plugs, STATION_PARAMS, context="Initialize FuelStation")
        self.TOTAL_PLUGS = plugs

        assert_constraint("PLUG_TYPE", plug_type, STATION_PARAMS, context="Initialize FuelStation")
        self.PLUG_TYPE = plug_type

        assert_constraint("PLUG_POWER", plug_power_kw, STATION_PARAMS, context="Initialize FuelStation")
        self.PLUG_POWER_KW = plug_power_kw

        self.avail_plugs = plugs

        self._logfile = logfile

        self.stats = dict()
        for stat in self._STATS:
            self.stats[stat] = 0

    def add_charge_event(self, veh, start_time, end_time, soc_i, soc_f, total_energy_kwh):
        """
        Updates VehicleBase tracking and logging w/ a new charge event.

        Updates VehicleBase & logging with energy consumed (total_energy_kwh)
        by charge event. Logs start & end time of charging event in addition to
        initial & final vehicle SOC & plug power & type to reconstruct detailed
        demand-side electical load curves.

        Parameters
        ----------
        veh: hive.vehicle.Vehicle
            Vehicle that completed the recharge event
        start_time: datetime.datetime
            Datetime that charge_event began
        end_time: datetime.datetime
            Datetime that charge_event concluded
        soc_i: double precision
            Initial fractional state of charge of vehicle's battery
        soc_f: double precision
            Final fractional state of charge of vehicle's battery
        total_energy_kwh: double precision
            Energy (in kWh) consumed during charge event

        Returns
        -------
        None
        """

        write_log({
            'id': self.ID,
            'plug_type': self.PLUG_TYPE,
            'plug_power_kw': self.PLUG_POWER_KW,
            'vehicle_id': veh.ID,
            'max_veh_acceptance_kw': veh.MAX_CHARGE_ACCEPTANCE_KW,
            'start_time': start_time,
            'end_time': end_time,
            'soc_i': soc_i,
            'soc_f': soc_f,
            'total_energy_kwh': total_energy_kwh
            },
            self._LOG_COLUMNS,
            self._logfile)

        self.stats['charge_cnt']+=1
        self.stats['total_energy_kwh']+=total_energy_kwh
