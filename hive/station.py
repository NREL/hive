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
    
    def __init__(self, station_id, latitude, longitude, logfile):
        self.station_id = station_id
        self.lat = latitude
        self.lon = longitude
        self.log = logfile
        self.charge_cnt = 0 #number of recharge events
        
    def add_recharge(self, veh_id, start_time, end_time, soc_i, soc_f):
        self.charge_cnt += 1
        with open(self.log, 'a') as f:
            writer = csv.writer(f)
            writer.writerow([self.station_id, veh_id, start_time, end_time, soc_i, soc_f])
            
        