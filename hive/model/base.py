from __future__ import annotations

from typing import Optional, NamedTuple, Tuple, Dict

from hive.model.coordinate import Coordinate
from hive.model.station import Station
from hive.util.typealiases import *


class Stall(NamedTuple):
    id: StallId

    in_use: bool = False
    vehicle_id: Optional[VehicleId] = None


class Base(NamedTuple):
    id: BaseId
    coordinate: Coordinate
    geoid: GeoId

    station: Station

    stalls: Dict[StallId, Stall]

    def checkout_stall(self, vehicle_id: VehicleId) -> Tuple[Base, Optional[Stall]]:
        avail_stalls = [stall for _, stall in self.stalls.items() if not stall.in_use]

        if len(avail_stalls) == 0:
            return self, None
        else:
            in_use_stall = avail_stalls[0]._replace(in_use=True, vehicle_id=vehicle_id)

            updated_stalls = self.stalls.copy()
            updated_stalls[in_use_stall.id] = in_use_stall

            return self._replace(stalls=updated_stalls), in_use_stall

    def return_stall(self, stall_id: StallId) -> Base:
        if stall_id not in self.stalls:
            raise KeyError('Attempting to return stall that this base doesnt have')
        elif not self.stalls[stall_id].in_use:
            return self
        else:
            returned_stall = self.stalls[stall_id]._replace(in_use=False, vehicle_id=None)

            updated_stalls = self.stalls.copy()
            updated_stalls[stall_id] = returned_stall

            return self._replace(stalls=updated_stalls)
