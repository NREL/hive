from __future__ import annotations

from enum import Enum
from typing import Optional

from hive.util.units import kw


class Charger(Enum):
    """
    Represents a charger in the simulation.
    """
    LEVEL_1 = 3.3  # kilowatt
    LEVEL_2 = 7.2  # kilowatt
    DCFC = 50  # kilowatt

    @property
    def power_kw(self) -> kw:
        """
        Returns the power of the charger in kilowatts

        :rtype: :py:obj:`kilowats`
        :return: charge power in kilowatts
        """
        return self.value

    @classmethod
    def from_string(cls, s: str) -> Optional[Charger]:
        """
        converts a string into a Charger

        :return: the named charger, or None if name wasn't valid
        """
        s_lower = s.lower()
        if s_lower in _charger_types:
            return _charger_types[s_lower]
        else:
            return None


_charger_types = {
    "level_1": Charger.LEVEL_1,
    "level_2": Charger.LEVEL_2,
    "dcfc": Charger.DCFC
}
