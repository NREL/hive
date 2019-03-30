"""
Configurations for running mist over one or more scenario.
"""

### Inputs ###

# LOCATION - Operating characteristics
##### REFACTOR - learn RN_SCALING_FACTOR + DISPATCH_SPEED from input data #####
#RN_SCALING_FACTOR = 1.4 #Scaling factor to approx on-road distance from haversine (1.32 NY; 1.4 Austin, Columbus)
#DISPATCH_SPEED = 20 #Avg driving speed on network - MPH (12 NY, 20 Austin)

# FLEET - Operating characteristics
MAX_FLEET_SIZE = 200 #Max number of vehicles in fleet
MAX_DISPATCH_MILES = 5 #Max miles allowed for dispatch

# FLEET - Vehicle 1 characteristics
BATTERY_CAPACITY_V1 = 80 #kWh
PASSENGERS_V1 = 7 #Max passenger capacity for fleet vehicles
EFFICIENCY_V1 = 275 #Operating efficiency - Wh/mile
CHARGE_ACCEPTANCE_V1 = 150 #Max charge acceptance - kW
PCT_OF_FLEET_V1 = 0.33 #Fraction of fleet w/ vehicle characteristics

# FLEET - Vehicle 2 characteristics
BATTERY_CAPACITY_V2 = 80 #kWh
PASSENGERS_V2 = 7 #Max passenger capacity for fleet vehicles
EFFICIENCY_V2 = 275 #Operating efficiency - Wh/mile
CHARGE_ACCEPTANCE_V2 = 150 #Max charge acceptance - kW
PCT_OF_FLEET_V2 = 0.33 #Fraction of fleet w/ vehicle characteristics

# FLEET - Vehicle 3 characteristics
BATTERY_CAPACITY_V3 = 80 #kWh
PASSENGERS_V3 = 7 #Max passenger capacity for fleet vehicles
EFFICIENCY_V3 = 275 #Operating efficiency - Wh/mile
CHARGE_ACCEPTANCE_V3 = 150 #Max charge acceptance - kW
PCT_OF_FLEET_V1 = 0.33 #Fraction of fleet w/ vehicle characteristics

# REFUEL - Operating characteristics
CHARGING_SCENARIO = 'Constrained' #'Constrained' = sited DC + L2 stations; 'Unconstrained' = Ubiquitous
MIN_SOC_REMAINING = 0.05 #Min SOC that can remain after a request; Necessary for locating charger
MINUTES_BEFORE_CHARGE = 0.5 #Minutes that a vehicle will remain idle before it begins to charge
UBIQUITOUS_CHARGER_POWER = 7.2 #kW - Only used if CHARGING_SCENARIO = 'Unconstrained'
STATION_LOWER_SOC_CHARGE_THRESH = 0.2 #Vehicle will travel to station to charge when SOC is detected below thresh
STATION_UPPER_SOC_CHARGE_THRESH = 0.8 #Upper threshold for SOC when charging @ station; Vehicle will stop charging when thresh is met
STATION_LOCATION_FILE = 'data/aus_fuel_stations.csv'

# OUTPUT - File paths
CLUSTER_PATH = '/data/mbap_shared/honda_data/clusters/austin/'
CLUSTER_FILES = [CLUSTER_PATH + 'austin_pools_2017_02_01_1000_10_os_2.p', #List of paths for .p request files to simulate over
                 CLUSTER_PATH + 'austin_pools_2017_02_02_1000_10_os_2.p']
REQUEST_PATH = '/data/mbap_shared/honda_data/requests/'
LOG_PATH = '/data/mbap_shared/honda_data/sim_logs/'
