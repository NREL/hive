"""
List of expected environment parameters and their upper and lower bounds
respectively.
"""
ENV_PARAMS = {
    'LOWER_SOC_THRESH_DCFC': (0,100),
    'UPPER_SOC_THRESH_DCFC': (0,100),
    'MAX_DISPATCH_MILES': (0, 10000),
    'MIN_ALLOWED_SOC': (0,100),
    "TRIP_REVENUE": (0,10000),
}
