from __future__ import annotations

from typing import NamedTuple

from hive.model.energy.energytype import EnergyType
from hive.util.typealiases import ChargerId


class Charger(NamedTuple):
    """
    Represents a charger in the simulation.
    """
    id: ChargerId
    energy_type: EnergyType
    rate: float
    units: str
