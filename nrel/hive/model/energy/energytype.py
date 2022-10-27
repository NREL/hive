from __future__ import annotations

from enum import Enum
from typing import Optional


class EnergyType(Enum):
    """
    a strict set of energy types recognized in HIVE
    """

    ELECTRIC = "kilowatt_hours"
    GASOLINE = "gallons_of_gasoline"

    @classmethod
    def from_string(cls, s: str) -> Optional[EnergyType]:
        values = {"electric": cls.ELECTRIC, "gasoline": cls.GASOLINE}
        if s in values.keys():
            return values[s]
        else:
            return None

    @property
    def units(self) -> str:
        return self.value
