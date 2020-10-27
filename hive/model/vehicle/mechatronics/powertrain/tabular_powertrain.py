from typing import Dict

import numpy as np

from hive.model.roadnetwork.link import Link
from hive.model.roadnetwork.routetraversal import Route
from hive.model.vehicle.mechatronics.powertrain.powertrain import Powertrain
from hive.util.units import valid_unit, get_unit_conversion


class TabularPowertrain(Powertrain):
    """
    builds a tabular, interpolated lookup model for energy consumption
    """

    def __init__(
            self,
            data: Dict[str, str],
    ):
        try:
            scale_factor = float(data['scale_factor'])
        except KeyError:
            scale_factor = 1

        expected_keys = [
            'consumption_model',
            'speed_units',
            'energy_units',
            'distance_units',
        ]
        for key in expected_keys:
            if key not in data:
                raise IOError(f"invalid input file for tabular power train model missing key {key}")

        if not valid_unit(data['speed_units']):
            raise TypeError(f"{data['speed_units']} not a recognized unit in hive")
        elif not valid_unit(data['distance_units']):
            raise TypeError(f"{data['distance_units']} not a recognized unit in hive")
        elif not valid_unit(data['energy_units']):
            raise TypeError(f"{data['energy_units']} not a recognized unit in hive")

        self.speed_units = data['speed_units']
        self.energy_units = data['energy_units']
        self.distance_units = data['distance_units']

        # linear interpolation function approximation via these lookup values
        consumption_model = sorted(data['consumption_model'], key=lambda x: x['speed'])
        self._consumption_speed = np.array(list(map(lambda x: x['speed'], consumption_model)))
        self._consumption_energy_per_distance = np.array(
            list(map(lambda x: x['energy_per_distance'], consumption_model))) * scale_factor

    def link_cost(self, link: Link) -> float:
        """
        uses mph tabular value to calculate energy over a link


        :param link: the link to calculate energy over.
        :return: energy in units captured by self.energy_units
        """
        # convert kilometers per hour to whatever units are used by this powertrain
        link_speed = link.speed_kmph * get_unit_conversion("kmph", self.speed_units)

        energy_per_distance = np.interp(link_speed,
                                        self._consumption_speed,
                                        self._consumption_energy_per_distance)
        # link distance is in kilometers
        link_distance = link.distance_km * get_unit_conversion("kilometer", self.distance_units)
        energy = energy_per_distance * link_distance
        return energy

    def energy_cost(self, route: Route) -> float:
        return sum([self.link_cost(link) for link in route])
