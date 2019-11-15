from __future__ import annotations

from typing import NamedTuple, Dict, Tuple, Optional

from hive.model.charger import Charger, ChargerType
from hive.model.coordinate import Coordinate
from hive.util.typealiases import *


class Station(NamedTuple):
    id: StationId
    coordinate: Coordinate
    geoid: GeoId

    chargers: Dict[ChargerId, Charger]

    def checkout_charger(self, charger_type: ChargerType, vehicle_id: VehicleId) -> Tuple[Station, Optional[Charger]]:
        chargers_of_type = [charger for _, charger in self.chargers.items() if charger.type == charger_type]
        avail_chargers = [charger for charger in chargers_of_type if not charger.in_use]

        if len(avail_chargers) == 0:
            return self, None
        else:
            in_use_charger = avail_chargers[0]._replace(in_use=True, vehicle_id=vehicle_id)

            updated_chargers = self.chargers.copy()
            updated_chargers[in_use_charger.id] = in_use_charger

            return self._replace(chargers=updated_chargers), in_use_charger

    def return_charger(self, charger_id: ChargerId) -> Station:
        if charger_id not in self.chargers:
            raise KeyError('Attempting to release charger that this station doesnt have')
        elif not self.chargers[charger_id].in_use:
            return self
        else:
            charger = self.chargers[charger_id]
            
            released_charger = charger._replace(in_use=False, vehicle_id=None)

            updated_chargers = self.chargers.copy()
            updated_chargers[charger_id] = released_charger
            
            return self._replace(chargers=updated_chargers)

