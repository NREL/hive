from __future__ import annotations

from enum import Enum
from typing import Optional, Tuple

from hive.util.units import Kw


class Charger(Enum):
    """
    Represents a charger in the simulation.
    """
    LEVEL_1 = 3.3  # kilowatt
    LEVEL_2 = 7.2  # kilowatt
    DCFC = 50  # kilowatt

    @property
    def power_kw(self) -> Kw:
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
        if s_lower in _CHARGER_TYPES:
            return _CHARGER_TYPES[s_lower]
        else:
            return None

    @classmethod
    def to_tuple(cls) -> Tuple[Charger, ...]:
        return cls.LEVEL_1, cls.LEVEL_2, cls.DCFC


_CHARGER_TYPES = {
    "level_1": Charger.LEVEL_1,
    "level_2": Charger.LEVEL_2,
    "dcfc": Charger.DCFC
}
