from typing import Optional

import h3

from hive.util import GeoId, SimulationStateError


def same_simulation_location(a: GeoId,
                             b: GeoId,
                             sim_h3_resolution: int,
                             override_resolution: Optional[int]) -> bool:
    """
    tests if two geoids are at the same location in the simulation. allows for overriding test resolution to a parent level.


    :param a: first geoid
:param b: second geoid

    :param sim_h3_resolution: resolution we want to compare at

    :param override_resolution: an overriding h3 spatial resolution, or, none to use this sim's default res
    :return: True/False, or, a SimulationStateError
    """
    if override_resolution is None:
        return a == b
    elif override_resolution > sim_h3_resolution:
        return False
    elif override_resolution == sim_h3_resolution:
        return a == b

    a_parent = h3.h3_to_parent(a, override_resolution)
    b_parent = h3.h3_to_parent(b, override_resolution)
    return a_parent == b_parent
