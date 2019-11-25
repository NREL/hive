import functools as ft
from typing import Dict, TypedDict, List

import numpy as np

from hive.model.energy.energytype import EnergyType
from hive.model.energy.powertrain.powertrain import Powertrain
from hive.model.roadnetwork.property_link import PropertyLink
from hive.model.roadnetwork.routetraversal import Route
from hive.util.typealiases import Kw, PowertrainId


class BEVTabularInput(TypedDict):
    name: str
    type: str
    charging_model: List[Dict[float, float]]
    consumption_model: List[Dict[float, float]]


class BEVTabularPowertrain(Powertrain):
    """
    builds a tabular, interpolated lookup model from a file
    for energy charge and consumption
    """

    def __init__(self, data: BEVTabularInput):
        if 'name' not in data and \
                'consumption_model' not in data and \
                'charging_model' not in data:
            raise IOError("invalid input file for tabular powertrain model")

        self.id = data['name']

        # linear interpolation function approximation via these lookup values
        consumption_model = sorted(data['consumption_model'], key=lambda x: x['mph'])
        self._consumption_mph = sorted(list(map(lambda x: x['mph'], consumption_model)))
        self._consumption_whmi = list(map(lambda x: x['whmi'], consumption_model))

        charging_model = sorted(data['charging_model'], key=lambda x: x['soc'])
        self._charging_soc = list(map(lambda x: x['soc'], charging_model))
        self._charging_c_kw = list(map(lambda x: x['kw'], charging_model))

    def get_id(self) -> PowertrainId:
        return self.id

    def get_energy_type(self) -> EnergyType:
        return EnergyType.ELECTRIC

    def property_link_cost(self, property_link: PropertyLink) -> Kw:
        watt_per_mile = np.interp(property_link.speed, self._consumption_mph, self._consumption_whmi)
        return watt_per_mile * property_link.distance

    def energy_cost(self, route: Route) -> Kw:
        return ft.reduce(
            lambda acc, link: acc + self.property_link_cost(link),
            route,
            0.0
        )



