from __future__ import annotations

from enum import Enum

from hive.util.typealiases import *


class Charger(Enum):
    LEVEL_1 = 3.3
    LEVEL_2 = 7.2
    DCFC = 50

    @property
    def power(self) -> Kw:
        return self.value
