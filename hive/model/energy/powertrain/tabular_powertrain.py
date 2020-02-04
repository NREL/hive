import functools as ft
from typing import Dict, TypedDict, List

import numpy as np

from hive.model.energy.energytype import EnergyType
from hive.model.energy.powertrain.powertrain import Powertrain
from hive.model.roadnetwork.property_link import PropertyLink
from hive.model.roadnetwork.routetraversal import Route
from hive.util.typealiases import PowertrainId
from hive.util.units import KwH, KMPH_TO_MPH, KM_TO_MILE, WH_TO_KWH


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
        self._consumption_mph = np.array(list(map(lambda x: x['mph'], consumption_model)))  # miles/hour
        self._consumption_whmi = np.array(list(map(lambda x: x['whmi'], consumption_model)))  # watthour/mile

    def get_id(self) -> PowertrainId:
        return self.id

    def get_energy_type(self) -> EnergyType:
        return EnergyType.ELECTRIC

    def property_link_cost(self, property_link: PropertyLink) -> KwH:
        """
        uses mph tabular value to calculate energy over a link

        :param property_link: the property link to calculate energy over.
        :return: energy in kilowatt-hours
        """
        # link speed is in kilometer/hour
        link_speed_mph = property_link.speed_kmph * KMPH_TO_MPH  # mph
        watthour_per_mile = np.interp(link_speed_mph,
                                      self._consumption_mph,
                                      self._consumption_whmi)  # watthour / mile
        # link distance is in kilometers
        energy_wh = (watthour_per_mile * property_link.distance_km * KM_TO_MILE)  # watthour
        energy_kwh = energy_wh * WH_TO_KWH  # kilowatthour
        return energy_kwh

    def energy_cost(self, route: Route) -> KwH:
        return ft.reduce(
            lambda acc, link: acc + self.property_link_cost(link),
            route,
            0.0
        )
