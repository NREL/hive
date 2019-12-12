from __future__ import annotations

from enum import Enum

from hive.util.units import unit, kw


class Charger(Enum):
    LEVEL_1 = 3.3 * unit.kilowatt
    LEVEL_2 = 7.2 * unit.kilowatt
    DCFC = 50 * unit.kilowatt

    @property
    def power(self) -> kw:
        return self.value
