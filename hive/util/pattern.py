vehicle_regex = r"^([\w]+),(\d+\.?\d*),(\d+\.?\d*),(\w+),(\w+),(\d+\.?\d*),(\d+\.?\d*)$"
"""
recognizes csv rows from a file with the following header:
0  1   2   3          4           5               6
id,lat,lon,powertrain,energycurve,energy_capacity,initial_soc
"""
