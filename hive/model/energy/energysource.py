from __future__ import annotations

import math
from typing import NamedTuple

from hive.model.energy.powercurve import PowerCurve
from hive.util.typealiases import KwH, PowerCurveId, Time
from hive.util.exception import StateOfChargeError


class EnergySource(NamedTuple):
    """
    a battery has a battery type, capacity and a load
    """
    powercurve_id: PowerCurveId
    capacity: KwH
    load: KwH

    @classmethod
    def build(cls, powercurve_id: PowerCurveId, capacity: KwH, soc: float = 1.0) -> EnergySource:
        assert 0.0 <= soc <= 1.0, StateOfChargeError(
            f"constructing battery with illegal soc of {(soc * 100.0):.2f}")
        return EnergySource(powercurve_id, capacity, capacity * soc)

    def soc(self) -> float:
        return self.load / self.capacity

    def use_energy(self, fuel_used: KwH) -> EnergySource:
        updated_load = self.load - fuel_used
        assert updated_load >= 0.0, StateOfChargeError("Battery fell below 0% SoC")
        return self._replace(load=updated_load)

    def load_energy(self, powercurve: PowerCurve, time: Time):
        rate = powercurve.energy_rate(self)
        effect = rate * time
        updated_load = math.min(self.capacity, self.load + effect)
        return self._replace(load=updated_load)

    def __repr__(self) -> str:
        return f"Battery({self.type},cap={self.capacity}, load={self.load}/{(self.soc() * 100.0):.2f}%)"
