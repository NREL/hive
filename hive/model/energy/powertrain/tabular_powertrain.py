import functools as ft
from typing import Dict, TypedDict, List

import numpy as np

from hive.model.energy.energytype import EnergyType
from hive.model.energy.powertrain.powertrain import Powertrain
from hive.model.roadnetwork.property_link import PropertyLink
from hive.model.roadnetwork.routetraversal import Route
from hive.util.helpers import UnitOps
from hive.util.typealiases import Kw, PowertrainId


class TabularPowertrainInput(TypedDict):
    name: str
    type: str
    consumption_model: List[Dict[float, float]]


class TabularPowertrain(Powertrain):
    """
    builds a tabular, interpolated lookup model from a file
    for energy consumption
    """

    def __init__(self, data: TabularPowertrainInput):
        if 'name' not in data and \
                'consumption_model' not in data:
            raise IOError("invalid input file for tabular powertrain model")

        self.id = data['name']

        # linear interpolation function approximation via these lookup values
        consumption_model_kmph = []
        for entry in data['consumption_model']:
            consumption_model_kmph.append(TabularPowertrain.convert_to_internal_units(entry))

        consumption_model = sorted(consumption_model_kmph, key=lambda x: x['kmph'])
        self._consumption_kmph = np.array(list(map(lambda x: x['kmph'], consumption_model)))
        self._consumption_whkm = np.array(list(map(lambda x: x['whkm'], consumption_model)))

    def get_id(self) -> PowertrainId:
        return self.id

    def get_energy_type(self) -> EnergyType:
        return EnergyType.ELECTRIC

    def property_link_cost(self, property_link: PropertyLink) -> Kw:
        """
        uses mph tabular value and
        :param property_link:
        :return:
        """
        watt_per_km = np.interp(property_link.speed, self._consumption_kmph, self._consumption_whkm)
        return watt_per_km * property_link.distance

    def energy_cost(self, route: Route) -> Kw:
        return ft.reduce(
            lambda acc, link: acc + self.property_link_cost(link),
            route,
            0.0
        )

    @classmethod
    def convert_to_internal_units(cls, entry: Dict[str, float]):
        if "mph" in entry.keys() and "whmi" in entry.keys():
            return {
                    "kmph": UnitOps.mph_to_km(entry["mph"]),
                    "whkm": UnitOps.miles_to_km(entry["whmi"])
            }
        elif "kmph" in entry.keys() and "whkm" in entry.keys():
            return entry
        else:
            raise AttributeError(f"energy consumption entry missing entry for either mph or kmph: {entry}")
