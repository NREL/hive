from __future__ import annotations
from typing import NamedTuple

import immutables

from hive.config import HiveConfig
from hive.util.typealiases import PowercurveId, PowertrainId
from hive.util.helpers import DictOps
from hive.model.energy.powertrain import Powertrain
from hive.model.energy.powercurve import Powercurve


class Environment(NamedTuple):
    """
    Environment variables for hive.

    :param config: hive config object.
    :type config: :py:obj:`HiveConfig`
    """
    config: HiveConfig
    powertrains: immutables.Map[PowertrainId, Powertrain] = immutables.Map()
    powercurves: immutables.Map[PowercurveId, Powercurve] = immutables.Map()

    def add_powertrain(self, powertrain: Powertrain) -> Environment:
        """
        Adds a powertrain to the environment
        :param powertrain:
        :return:
        """
        if not isinstance(powertrain, Powertrain):
            raise TypeError(f"sim.powertrain requires a powertrain but received {type(powertrain)}")

        return self._replace(
            powertrains=DictOps.add_to_dict(self.powertrains, powertrain.get_id(), powertrain),
        )

    def add_powercurve(self, powercurve: Powercurve) -> Environment:
        """
        Adds a powercurve to the environment
        :param powercurve:
        :return:
        """
        if not isinstance(powercurve, Powercurve):
            raise TypeError(f"env.add_powercurve requires a powercurve but received {type(powercurve)}")

        return self._replace(
            powercurves=DictOps.add_to_dict(self.powercurves, powercurve.get_id(), powercurve),
        )
