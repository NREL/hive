"""
Charging station objects used in the HIVE simulation platform.
"""

from hive.constraints import STATION_PARAMS
from hive.utils import assert_constraint, generate_csv_row
from hive import units

import sys


class FuelStation:
    """
    Base class for electric vehicle charging station.

    Parameters
    ----------
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
    plug_power_kw: float
        Plug power in kW
    clock: hive.utils.Clock
        simulation clock shared across the simulation to track simulation time steps.
    """
    LOG_COLUMNS = [
            'ID',
            'sim_time',
            'time',
            'vehicles_charging',
            'power_usage_kw',
            'energy_dispensed_kwh',
            ]

    def __init__(
                self,
                station_id,
                latitude,
                longitude,
                plugs,
                plug_type,
                plug_power_kw,
                clock,
                log,
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

        self._clock = clock

        self.history = []

        self.avail_plugs = plugs

        self._energy_dispensed_kwh = 0

        self.log = log

    def _log(self):
        power_usage_kw = self._energy_dispensed_kwh / (self._clock.TIMESTEP_S * units.SECONDS_TO_HOURS)
        vehicles_charging = round(power_usage_kw/self.PLUG_POWER_KW)

        info = [
            ('ID', self.ID),
            ('sim_time', self._clock.now),
            ('time', self._clock.get_time()),
            ('vehicles_charging', vehicles_charging),
            ('power_usage_kw', power_usage_kw),
            ('energy_dispensed_kwh', self._energy_dispensed_kwh),
            ]

        self.log.info(generate_csv_row(info, self.LOG_COLUMNS))

    def dispense_energy(self):
        """
        Returns the amount of energy that the station dispenses during one simulation
        time step.

        Returns
        -------
        energy_kwh: float
            Amount of energy dispensed in a time step. Units are kilowatt-hours.
        """
        timestep_h = self._clock.TIMESTEP_S * units.SECONDS_TO_HOURS
        energy_kwh = self.PLUG_POWER_KW * timestep_h

        self._energy_dispensed_kwh += energy_kwh

        return energy_kwh

    def step(self):
        """
        Called each time step. Station updates its state.
        """
        if self._energy_dispensed_kwh > 0:
            self._log()

        self._energy_dispensed_kwh = 0
