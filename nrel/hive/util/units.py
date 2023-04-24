from __future__ import annotations

from enum import Enum, auto
from typing import Dict


class Unit(Enum):
    MPH = auto()
    KMPH = auto()
    MILES = auto()
    KILOMETERS = auto()
    WATT_HOUR = auto()
    KILOWATT_HOUR = auto()
    GALLON_GASOLINE = auto()

    @classmethod
    def from_string(cls, string: str) -> Unit:
        s = string.strip().lower()
        if s in ["mph", "miles_per_hour"]:
            return Unit.MPH
        if s in ["kmph", "kilomters_per_hour"]:
            return Unit.KMPH
        if s in ["mile", "miles", "mi"]:
            return Unit.MILES
        if s in ["kilometers", "kilometer", "km"]:
            return Unit.KILOMETERS
        if s in ["watthour", "watt-hour", "watt_hour", "wh"]:
            return Unit.WATT_HOUR
        if s in ["kilowatthour", "kilowatt-hour", "kilowatt_hour", "kwh"]:
            return Unit.KILOWATT_HOUR
        if s in ["gge", "gallon_gasoline", "gal_gas"]:
            return Unit.GALLON_GASOLINE
        else:
            raise ValueError(f"Could not find unit from {string}")


## TYPE ALIAS
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

## CONVERSIONS
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

UNIT_CONVERSIONS: Dict[Unit, Dict[Unit, float]] = {
    Unit.MPH: {
        Unit.KMPH: MPH_TO_KMPH,
    },
    Unit.KMPH: {
        Unit.MPH: KMPH_TO_MPH,
    },
    Unit.MILES: {
        Unit.KILOMETERS: M_TO_KM,
    },
    Unit.KILOMETERS: {
        Unit.MILES: KM_TO_MILE,
    },
    Unit.WATT_HOUR: {
        Unit.KILOWATT_HOUR: WH_TO_KWH,
    },
    Unit.KILOWATT_HOUR: {
        Unit.WATT_HOUR: KWH_TO_WH,
    },
}


def get_unit_conversion(from_unit: Unit, to_unit: Unit) -> float:
    if from_unit == to_unit:
        return 1

    from_conversion = UNIT_CONVERSIONS.get(from_unit)
    if from_conversion is None:
        raise ValueError(f"no unit conversion for from_unit: {from_unit}")

    to_conversion = from_conversion.get(to_unit)
    if to_conversion is None:
        raise ValueError(f"no unit conversion for to_unit: {to_unit}")

    return to_conversion
