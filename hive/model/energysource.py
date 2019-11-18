from __future__ import annotations

from enum import Enum
from typing import NamedTuple

from hive.util.typealiases import KwH
from hive.util.exception import StateOfChargeError


class EnergyType(Enum):
    """
    a strict set of energy types recognized in HIVE
    """
    ELECTRIC = 0
    GASOLINE = 1


class EnergySource(NamedTuple):
    """
    a battery has a battery type, capacity and a load
    """
    type: EnergyType
    capacity: KwH
    load: KwH

    @classmethod
    def build(cls, _type: EnergyType, _capacity: KwH, _soc: float = 1.0) -> EnergySource:
        assert 0.0 <= _soc <= 1.0, StateOfChargeError(
            f"constructing battery {_type} with illegal soc of {(_soc * 100.0):.2f}")
        return cls(_type, _capacity, _capacity * _soc)

    def soc(self) -> float:
        return self.load / self.capacity

    def use_energy(self, fuel_used: KwH) -> EnergySource:
        updated_load = self.load - fuel_used
        assert updated_load >= 0.0, StateOfChargeError("Battery fell below 0% SoC")
        return self._replace(load=updated_load)

    def load_energy(self, rate):
        updated_load = self.load + 1.0 # todo: whatever needs to happen here
        return self._replace(load=updated_load)

    def __repr__(self) -> str:
        return f"Battery({self.type},cap={self.capacity}, load={self.load}/{(self.soc() * 100.0):.2f}%)"
