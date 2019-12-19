import functools as ft
from typing import Dict, TypedDict, List

import numpy as np

from hive.model.energy.energytype import EnergyType
from hive.model.energy.powertrain.powertrain import Powertrain
from hive.model.roadnetwork.property_link import PropertyLink
from hive.model.roadnetwork.routetraversal import Route
from hive.util.typealiases import PowertrainId
from hive.util.units import unit, kwh


class TabularPowertrainInput(TypedDict):
    """
    Input parameters for a TabularPowertrain"
    """
    name: str
    type: str
    consumption_model: List[Dict[float, float]]


class TabularPowertrain(Powertrain):
    """
    builds a tabular, interpolated lookup model from a file for energy consumption
    """

    def __init__(self, data: TabularPowertrainInput):
        if 'name' not in data and \
                'consumption_model' not in data:
            raise IOError("invalid input file for tabular powertrain model")

        self.id = data['name']

        # linear interpolation function approximation via these lookup values

        consumption_model = sorted(data['consumption_model'], key=lambda x: x['mph'])
        self._consumption_mph = np.array(list(map(lambda x: x['mph'], consumption_model))) * (unit.miles/unit.hour)
        self._consumption_whmi = np.array(list(map(lambda x: x['whmi'], consumption_model))) * (unit.watthour/unit.mile)

    def get_id(self) -> PowertrainId:
        return self.id

    def get_energy_type(self) -> EnergyType:
        return EnergyType.ELECTRIC

    def property_link_cost(self, property_link: PropertyLink) -> kwh:
        """
        uses mph tabular value to calculate energy over a link

        :param property_link: the property link to calculate energy over.
        :return: energy in kilowatt-hours
        """
        watthour_per_mile = np.interp(property_link.speed.to((unit.miles / unit.hour)),
                                      self._consumption_mph,
                                      self._consumption_whmi) * (unit.watthour / unit.mile)
        energy_wh = watthour_per_mile * property_link.distance.to(unit.mile)
        return energy_wh.to(unit.kilowatthour)

    def energy_cost(self, route: Route) -> kwh:
        return ft.reduce(
            lambda acc, link: acc + self.property_link_cost(link),
            route,
            0.0 * unit.kilowatthour
        )

