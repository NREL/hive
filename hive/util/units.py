# Energy
KwH = float  # kilowatt-hours
J = float  # joules

# Power
Kw = float  # kilowatt

# Distance
Meters = float  # meters
Kilometers = float  # kilometers
Feet = float  # feet
Miles = float  # miles

# Speed
Mph = float  # miles per hour
Kmph = float  # kilometers per hour

# Time
Seconds = int  # seconds
Hours = float  # hours

# Dimensionless
Percentage = float  # between 0-100
Ratio = float  # between 0-1

# Conversions
#    Time
HOURS_TO_SECONDS = 3600


def hours_to_seconds(hours: Hours) -> Seconds:
    seconds = hours * HOURS_TO_SECONDS
    return int(seconds)


SECONDS_TO_HOURS = 1 / 3600

#    Speed
KMPH_TO_MPH = 0.621371

#    Distance
KM_TO_MILE = 0.621371

#    Energy
WH_TO_KWH = 0.001
