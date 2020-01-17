# Energy
kwh = float  # kilowatt-hours
J = float  # joules

# Power
kw = float  # kilowatt

# Distance
m = float  # meters
km = float  # kilometers
ft = float  # feet
mi = float  # miles

# Speed
mph = float  # miles per hour
kmph = float  # kilometers per hour

# Time
seconds = int  # seconds
hours = float  # hours

# Dimensionless
Percentage = float  # between 0-100
Ratio = float  # between 0-1

# Conversions
#    Time
HOURS_TO_SECONDS = 3600


def hours_to_seconds(hours: hours) -> seconds:
    seconds = hours * HOURS_TO_SECONDS
    return int(seconds)


SECONDS_TO_HOURS = 1 / 3600

#    Speed
KMPH_TO_MPH = 0.621371

#    Distance
KM_TO_MILE = 0.621371

#    Energy
WH_TO_KWH = 0.001
