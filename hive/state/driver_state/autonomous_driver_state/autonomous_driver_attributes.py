from typing import NamedTuple

from hive.util import VehicleId


class AutonomousDriverAttributes(NamedTuple):
    """
    the set of attributes which persist for an autonomous driver
    """
    vehicle_id: VehicleId
    # agencies we can use?




