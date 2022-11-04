# Energy
from typing import Dict


KwH = float  # kilowatt-hours
J = float  # joules
KwH_per_H = float
GallonGasoline = float

# Power/Rate
Kw = float  # kilowatt
GallonPerSecond = float
GallonPerHour = float

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
MPH_TO_KMPH = 1 / KMPH_TO_MPH

#    Distance
KM_TO_MILE = 0.621371
MILE_TO_KM = 1.609344
M_TO_KM = 1 / 1000

#    Energy Rate
WattHourPerMile = float
WH_TO_KWH = 0.001
KWH_TO_WH = 1 / WH_TO_KWH
MilesPerGallon = float

UNIT_CONVERSIONS: Dict[str, Dict[str, float]] = {
    "mph": {"kmph": MPH_TO_KMPH,},
    "kmph": {"mph": KMPH_TO_MPH,},
    "mile": {"kilometer": M_TO_KM,},
    "kilometer": {"mile": KM_TO_MILE,},
    "watthour": {"kilowatthour": WH_TO_KWH,},
    "kilowatthour": {"watthour": KWH_TO_WH,},
    "gal_gas": {},
}


def valid_unit(unit: str) -> bool:
    return unit in UNIT_CONVERSIONS.keys()


def get_unit_conversion(from_unit: str, to_unit: str) -> float:
    if not valid_unit(from_unit):
        raise TypeError(f"{from_unit} not a recognized unit in hive")
    elif not valid_unit(to_unit):
        raise TypeError(f"{to_unit} not a recognized unit in hive")
    elif from_unit == to_unit:
        return 1

    from_conversion = UNIT_CONVERSIONS.get(from_unit)
    if from_conversion is None:
        raise ValueError(f"no unit conversion for from_unit: {from_unit}")

    to_conversion = from_conversion.get(to_unit)
    if to_conversion is None:
        raise ValueError(f"no unit conversion for to_unit: {to_unit}")

    return to_conversion
