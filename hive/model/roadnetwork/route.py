from typing import Tuple

from hive.model.roadnetwork.property_link import PropertyLink

Route = Tuple[PropertyLink, ...]
"""
any route in the system is a tuple of PropertyLinks
"""