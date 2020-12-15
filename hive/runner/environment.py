from __future__ import annotations

from typing import NamedTuple, TYPE_CHECKING, FrozenSet

import immutables

if TYPE_CHECKING:
    from hive.model.energy.charger import Charger
    from hive.model.vehicle.mechatronics.mechatronics_interface import MechatronicsInterface
    from hive.reporting import Reporter
    from hive.config import HiveConfig
    from hive.util.typealiases import MechatronicsId, ChargerId, ScheduleId, ScheduleFunction, MembershipId


class Environment(NamedTuple):
    """
    Environment of this Hive Simulation.

    """
    config: HiveConfig
    reporter: Reporter
    mechatronics: immutables.Map[MechatronicsId, MechatronicsInterface] = immutables.Map()
    chargers: immutables.Map[ChargerId, Charger] = immutables.Map()
    schedules: immutables.Map[ScheduleId, ScheduleFunction] = immutables.Map()
    fleet_ids: FrozenSet[MembershipId] = frozenset()
