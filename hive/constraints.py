"""
List of expected environment parameters and their upper and lower bounds
respectively.
"""
ENV_PARAMS = {
    'MAX_WAIT_TIME_MINUTES': ('between', 0, 6000),
    'LOWER_SOC_THRESH_DCFC': ('between', 0,100),
    'UPPER_SOC_THRESH_DCFC': ('between', 0,100),
    'MAX_DISPATCH_MILES': ('between', 0, 10000),
    'RN_SCALING_FACTOR': ('between', 0, 5),
    'DISPATCH_MPH': ('between', 0, 100),
    'MIN_ALLOWED_SOC': ('between', 0,100),
    "TRIP_REVENUE": ('between', 0,10000),
}

VEH_PARAMS = {
    'BATTERY_CAPACITY': ('between', 1, 1000), #kwh
}
