from pint import UnitRegistry

unit = UnitRegistry()
Q_ = unit.Quantity

# Unit type hints for commonly used units.

# Energy
kwh = type(unit.kilowatthours)  # kilowatt-hours
J = type(unit.joules)  # joules

# Power
kw = type(unit.kilowatt)  # kilowatt

# Distance
m = type(unit.meter)  # meters
km = type(unit.kilometer)  # kilometers
ft = type(unit.feet)  # feet
mi = type(unit.mi)  # miles

# Speed
mph = type(unit.miles/unit.hour)  # miles per hour
kmph = type(unit.kilometers/unit.hour)  # kilometers per hour

# Time
s = type(unit.second)  # seconds
h = type(unit.hour)  # hours

# Dimensionless
Percentage = float  # between 0-100
Ratio = float  # between 0-1
