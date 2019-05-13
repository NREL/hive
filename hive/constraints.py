"""
List of expected environment parameters and their upper and lower bounds
respectively.
"""
ENV_PARAMS = {
    'MAX_WAIT_TIME_MINUTES': (0, 6000),
    'LOWER_SOC_THRESH_DCFC': (0,100),
    'UPPER_SOC_THRESH_DCFC': (0,100),
    'MAX_DISPATCH_MILES': (0, 10000),
    'RN_SCALING_FACTOR': (0, 5),
    'DISPATCH_MPH': (0, 100),
    'MIN_ALLOWED_SOC': (0,100),
    "TRIP_REVENUE": (0,10000),
}
