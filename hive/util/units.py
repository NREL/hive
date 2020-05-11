# Energy
KwH = float  # kilowatt-hours
J = float  # joules
KwH_per_H = float

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

# Currency
Currency = float  # an arbitrary currency type, reified in hiveconfig.scenario.currency_name

# Dimensionless
Percentage = float  # between 0-100
Ratio = float  # between 0-1

# Conversions
#    Time
HOURS_TO_SECONDS = 3600


def hours_to_seconds(hours: Hours) -> Seconds:
    seconds = hours * HOURS_TO_SECONDS
    return int(seconds)


SECONDS_IN_HOUR = 3600

SECONDS_TO_HOURS = 1 / 3600

#    Speed
KMPH_TO_MPH = 0.621371
MPH_TO_KMPH = 1/KMPH_TO_MPH

#    Distance
KM_TO_MILE = 0.621371
MILE_TO_KM = 1.609344
M_TO_KM = 1/1000

#    Energy
WattHourPerMile = float
WH_TO_KWH = 0.001


