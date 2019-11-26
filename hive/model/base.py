from __future__ import annotations

from typing import Optional, NamedTuple

from hive.model.station import Station
from hive.util.exception import SimulationStateError
from hive.util.typealiases import *


class Base(NamedTuple):
    id: BaseId
    geoid: GeoId

    station: Optional[Station]

    total_stalls: int
    available_stalls: int

    @classmethod
    def build(cls,
              id: BaseId,
              geoid: GeoId,
              station: Optional[Station],
              total_stalls: int
              ):
        return cls(id, geoid, station, total_stalls, total_stalls)

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
