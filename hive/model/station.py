from __future__ import annotations

from typing import NamedTuple, Dict, Optional

from hive.model.energy.charger import Charger
from hive.util.exception import SimulationStateError
from hive.util.typealiases import *


class Station(NamedTuple):
    id: StationId
    geoid: GeoId

    total_chargers: Dict[Charger, int]
    available_chargers: Dict[Charger, int]

    @classmethod
    def build(cls,
              id: StationId,
              geoid: GeoId,
              total_chargers: Dict[Charger, int]
              ):
        return cls(id, geoid, total_chargers, total_chargers)

    def has_available_charger(self, charger: Charger) -> bool:
        if charger in self.total_chargers:
            if self.available_chargers[charger] > 0:
                return True

        return False

    def checkout_charger(self, charger: Charger) -> Optional[Station]:
        chargers = self.available_chargers[charger]

        if chargers < 1:
            return None
        else:
            updated_avail_chargers = self.available_chargers.copy()
            updated_avail_chargers[charger] -= 1

            return self._replace(available_chargers=updated_avail_chargers)

    def return_charger(self, charger: Charger) -> Optional[Station]:
        chargers = self.available_chargers[charger]
        if (chargers + 1) > self.total_chargers[charger]:
            raise SimulationStateError("Station already has max chargers of this type")
        else:
            updated_avail_chargers = self.available_chargers.copy()
            updated_avail_chargers[charger] += 1

            return self._replace(available_chargers=updated_avail_chargers)
