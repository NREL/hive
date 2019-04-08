"""
Configurations for running mist over one or more scenario.
"""

STATION_LOCATION_FILE = 'inputs/charge_network/aus_fuel_stations.csv'

VEHICLE_PATH = 'inputs/vehicles/'
REQUEST_PATH = 'inputs/requests/'

# OUTPUT - File paths
CLUSTER_PATH = '/data/mbap_shared/honda_data/clusters/austin/'
CLUSTER_FILES = [CLUSTER_PATH + 'austin_pools_2017_02_01_1000_10_os_2.p', #List of paths for .p request files to simulate over
                 CLUSTER_PATH + 'austin_pools_2017_02_02_1000_10_os_2.p']

LOG_PATH = '/data/mbap_shared/honda_data/sim_logs/'
