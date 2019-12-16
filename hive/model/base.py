from __future__ import annotations

from typing import Optional, NamedTuple

from hive.util.exception import SimulationStateError
from hive.util.typealiases import *


class Base(NamedTuple):
    id: BaseId
    geoid: GeoId
    total_stalls: int
    available_stalls: int
    station_id: Optional[StationId]

    @classmethod
    def build(cls,
              id: BaseId,
              geoid: GeoId,
              station_id: Optional[StationId],
              total_stalls: int
              ):
        return Base(id, geoid, total_stalls, total_stalls, station_id)

    def has_available_stall(self) -> bool:
        if self.available_stalls > 0:
            return True
        else:
            return False

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
