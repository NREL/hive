from __future__ import annotations

from typing import Optional, NamedTuple

from hive.model.coordinate import Coordinate
from hive.model.station import Station
from hive.util.exception import SimulationStateError
from hive.util.typealiases import *


class Base(NamedTuple):
    id: BaseId
    coordinate: Coordinate
    geoid: GeoId

    station: Station

    total_stalls: int
    available_stalls: int

    def checkout_stall(self) -> Optional[Base]:
        stalls = self.available_stalls
        if stalls < 1:
            return None
        else:
            return self._replace(available_stalls=stalls - 1)

    def return_stall(self) -> Optional[Base]:
        stalls = self.available_stalls
        if (stalls + 1) > self.total_stalls:
            raise SimulationStateError('Base already has maximum sta')
        else:
            return self._replace(available_stalls=stalls + 1)
