"""
Configurations for running hive over one or more scenario.
"""
# System
ARNAUD=False
if ARNAUD:
    N_PROCESSES = 40 #arg for multiprocessing.Pool

# In-Paths
IN_PATH = 'inputs/'
CHARGE_NETWORK_FILE = 'inputs/charge_network/aus_fuel_stations.csv'
OPERATING_AREA_PATH = 'inputs/operating_area/test/rideaustin/'
VEHICLE_PATH = 'inputs/vehicles/'
REQUEST_PATH = 'inputs/requests/test/rideaustin/'

# Out-Paths
if ARNAUD:
    OUT_PATH = '/data/mbap_shared/'
else:
    OUT_PATH = 'outputs/' #local path

VERBOSE = True
