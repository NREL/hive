"""
List of expected environment parameters and their upper and lower bounds
respectively.
"""
ENV_PARAMS = {
    'MAX_ALLOWABLE_IDLE_MINUTES': ('between', 0, 6000),
    'LOWER_SOC_THRESH_STATION': ('between', 0,100),
    'UPPER_SOC_THRESH_STATION': ('between', 0,100),
    'MAX_DISPATCH_MILES': ('between', 0, 10000),
    'RN_SCALING_FACTOR': ('between', 1, 5),
    'DISPATCH_MPH': ('between', 0, 100),
    'MIN_ALLOWED_SOC': ('between', 0,100),
    "TRIP_REVENUE": ('between', 0,10000),
}

VEH_PARAMS = {
    'BATTERY_CAPACITY': ('greater_than', 0), #kwh
    'INITIAL_SOC': ('between_incl', 0, 1)
}

STATION_PARAMS = {
    'TOTAL_PLUGS': ('greater_than', 0),
    'PLUG_TYPE': ('in_set', ['AC', 'DC']),
    'PLUG_POWER': ('greater_than', 0), #kw
}
