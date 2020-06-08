from __future__ import annotations

from typing import Optional, Tuple, NamedTuple

from hive.util.typealiases import ChargerId
from hive.util.units import Kw


class Charger(NamedTuple):
    """
    Represents a charger_id in the simulation.
    """
    id: ChargerId
    power_kw: Kw  # kilowatt
