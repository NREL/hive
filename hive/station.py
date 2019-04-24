"""
Charging station object for mist algorithm
"""

import csv

class ChargeStation:
    """
    Base class for electric vehicle charging station.

    Inputs
    ------
    station_id : int
        Identifer assigned to FuelStation object
    latitude : double precision
        Latitude of station location
    longitude: double precision
        Longitude of station location
    logfile: str
        Path to fuel station log file

    Attributes
     ----------
    charge_cnt:
        Number of charge events
    """

    STATS = [
        'charge_cnt', #Number of recharge events
        ]

    def __init__(
                self,
                id,
                latitude,
                longitude,
                charge_power,
                plug_count,
                logfile
                ):

        self.id = id
        self.lat = latitude
        self.lon = longitude
        self.charge_power = charge_power
        self.plug_count = plug_count

        self._log = logfile

        self._stats = dict()
        for stat in self.STATS:
            self._stats[stat] = 0

    def add_recharge(self, veh_id, start_time, end_time, soc_i, soc_f):
        self._stats['charge_cnt'] += 1
        with open(self._log, 'a') as f:
            writer = csv.writer(f)
            writer.writerow([self.id, veh_id, start_time, end_time, soc_i, soc_f])

class Hub(ChargeStation):
    """
    Class for vehicle hub. Extends ChargeStation.
    """

    HUB_STATS = [
        'max_vehicles', #Max number of vehicles stationed during simulation.
        ]

    def __init__(
                self,
                id,
                latitude,
                longitude,
                charge_power,
                plug_count,
                capacity,
                logfile,
                ):

        super().__init__(id, latitude, longitude, charge_power, plug_count, logfile)
        self.capacity = capacity

        # Container for vehicles currently at the Hub.
        self.vehicles = []

        for stat in self.HUB_STATS:
            self._stats[stat] = 0
