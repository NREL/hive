"""
Configurations for running hive over one or more scenario.
"""
# System
arnaud=False
if arnaud:
    n_processes = 40 #arg for multiprocessing.Pool

# In-Paths
CHARGE_NETWORK_FILE = 'inputs/charge_network/aus_fuel_stations.csv'
OPERATING_AREA_FILE = 'inputs/operating_area/test/rideaustin/'
VEHICLE_PATH = 'inputs/vehicles/'
REQUEST_PATH = 'inputs/requests/test/rideaustin/'

# Out-Paths
if arnaud:
    OUT_PATH = '/data/mbap_shared/'
else:
    OUT_PATH = '~/Desktop/' #local path