from __future__ import annotations

from typing import NamedTuple, TYPE_CHECKING

import immutables
from hive.model.energy.energytype import EnergyType

from hive.model.energy.powercurve import Powercurve
from hive.model.energy.powertrain import Powertrain
from hive.model.vehicle.vehicle_type import VehicleType
from hive.util.helpers import DictOps

if TYPE_CHECKING:
    from hive.reporting import Reporter
    from hive.config import HiveConfig
    from hive.util.typealiases import PowercurveId, PowertrainId, VehicleTypeId


class Environment(NamedTuple):
    """
    Context of this Hive Simulation

    :param config: hive config object.
    :type config: :py:obj:`HiveConfig`
    :param reporter: logging system
    :type reporter: :py:obj:`Reporter`
    :param powertrains: the collection of powetrain models we are using
    :type powetrains: :py:obj:`immutable.Map[PowertrainId, Powertrain]`
    :param powercurves: the collection of powercurve models we are using
    :type powercurves: :py:obj:`immutable.Map[PowercurveId, Powercurve]`
    """
    config: HiveConfig
    reporter: Reporter
    powertrains: immutables.Map[PowertrainId, Powertrain] = immutables.Map()
    powercurves: immutables.Map[PowercurveId, Powercurve] = immutables.Map()
    vehicle_types: immutables.Map[VehicleTypeId, VehicleType] = immutables.Map()
    energy_types: immutables.Map[PowercurveId, EnergyType] = immutables.Map()

    sim_output_dir: str = ""  # todo: this should come from HiveConfig.IO

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
            energy_types=DictOps.add_to_dict(self.energy_types, powercurve.get_id(), powercurve.get_energy_type())
        )
