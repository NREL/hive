from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Tuple

if TYPE_CHECKING:
    from nrel.hive.util.units import Ratio, Kw, Seconds, KwH


class Powercurve(ABC):
    """
    a powertrain has a behavior where it calculates energy consumption in KwH
    """

    @abstractmethod
    def charge(
        self,
        start_soc: Ratio,
        full_soc: Ratio,
        power_kw: Kw,
        duration_seconds: Seconds = 1,  # seconds
    ) -> Tuple[KwH, Seconds]:
        """


        :param start_soc:
        :param full_soc:
        :param power_kw:
        :param duration_seconds:
        :return: the charge amount along with the time spent charging
        """
