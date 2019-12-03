from typing import TypedDict, Dict, List

import numpy as np

from hive.model.energy.energycurve.powercurve import PowerCurve
from hive.model.energy.energysource import EnergySource
from hive.model.energy.energytype import EnergyType
from hive.util.typealiases import Kw, PowerCurveId


class TabularPowerCurveInput(TypedDict):
    name: str
    type: str
    energy_type: str
    energy_curve: List[Dict[float, float]]


class TabularPowerCurve(PowerCurve):
    """
    builds a tabular, interpolated lookup model from a file
    for energy curves
    """

    def __init__(self, data: TabularPowerCurveInput):
        if 'name' not in data and \
                'charging_model' not in data:
            raise IOError("invalid input file for tabular energy curve model")

        self.id = data['name']
        self.energy_type = EnergyType.from_string(data['energy_type'])

        if self.energy_type is None:
            raise AttributeError(f"TabularEnergyModel initialized with invalid energy type {self.energy_type}")

        charging_model = sorted(data['energy_curve'], key=lambda x: x['soc'])
        self._charging_soc = np.array(list(map(lambda x: x['soc'], charging_model)))
        self._charging_c_kw = np.array(list(map(lambda x: x['kw'], charging_model)))

    def get_id(self) -> PowerCurveId:
        return self.id

    def get_energy_type(self) -> EnergyType:
        return self.energy_type

    def energy_rate(self, energy_source: EnergySource) -> Kw:
        """
         (estimated) energy rate due to fueling, based on an interpolated tabular lookup model
         :param energy_source: a vehicle's source of energy
         :return: energy rate in KwH for charging with the current state of the EnergySource
         """
        soc = energy_source.soc()
        soc_lookup = soc * 100
        gain = np.interp(soc_lookup, self._charging_soc, self._charging_c_kw)
        return gain

