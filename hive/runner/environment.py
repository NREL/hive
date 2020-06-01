from __future__ import annotations

from typing import NamedTuple, TYPE_CHECKING

import immutables

if TYPE_CHECKING:
    from hive.model.vehicle.mechatronics.mechatronics_interface import MechatronicsInterface
    from hive.reporting import Reporter
    from hive.config import HiveConfig
    from hive.util.typealiases import MechatronicsId


class Environment(NamedTuple):
    """
    Environment of this Hive Simulation

    """
    config: HiveConfig
    reporter: Reporter
    mechatronics: immutables.Map[MechatronicsId, MechatronicsInterface] = immutables.Map()
