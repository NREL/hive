from __future__ import annotations

from typing import NamedTuple

from nrel.hive.model.energy.energytype import EnergyType
from nrel.hive.util.typealiases import ChargerId


class Charger(NamedTuple):
    """
    Represents a charger in the simulation.
    """

    id: ChargerId
    energy_type: EnergyType
    rate: float
    units: str
