from __future__ import annotations

from enum import Enum
from typing import NamedTuple, Optional

from hive.util.typealiases import *


class ChargerType(Enum):
    LEVEL_1 = 0
    LEVEL_2 = 1
    DCFC = 3


class Charger(NamedTuple):
    id: ChargerId
    type: ChargerType
    power: Kw

    in_use: bool = False
    vehicle_id: Optional[VehicleId] = None
