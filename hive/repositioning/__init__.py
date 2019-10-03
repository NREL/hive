__doc__ = """
HIVE Repositioning Module

provides a specification and a delivery method for repositioning implementations into a simulation.

defining new repositioning modules requires 
1. creating a class which inherits from AbstractRepositioning,
2. "registering" the class by adding it to the '_valid_repositioning' dictionary in Repositioning.py 
"""