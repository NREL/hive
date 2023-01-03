from dataclasses import dataclass
from typing import Dict, Any

import numpy as np

from nrel.hive.model.roadnetwork.linktraversal import LinkTraversal
from nrel.hive.model.roadnetwork.routetraversal import Route
from nrel.hive.model.vehicle.mechatronics.powertrain.powertrain import Powertrain
from nrel.hive.util.units import Unit, get_unit_conversion


@dataclass(frozen=True)
class TabularPowertrain(Powertrain):
    """
    builds a tabular, interpolated lookup model for energy consumption
    """

    speed_units: Unit
    distance_units: Unit
    energy_units: Unit

    consumption_speed: np.ndarray
    consumption_energy_per_distance: np.ndarray

    @classmethod
    def from_data(
        self,
        data: Dict[str, Any],
    ):
        try:
            scale_factor = float(data["scale_factor"])
        except KeyError:
            scale_factor = 1

        expected_keys = [
            "consumption_model",
            "speed_units",
            "energy_units",
            "distance_units",
        ]
        for key in expected_keys:
            if key not in data:
                raise IOError(f"invalid input file for tabular power train model missing key {key}")

        try:
            speed_units = Unit.from_string(data["speed_units"])
            energy_units = Unit.from_string(data["energy_units"])
            distance_units = Unit.from_string(data["distance_units"])
        except ValueError as e:
            raise ValueError(
                "Failed to parse incoming units when building TabularPowertrain"
            ) from e

        # linear interpolation function approximation via these lookup values
        consumption_model = sorted(data["consumption_model"], key=lambda x: x["speed"])
        consumption_speed = np.array(list(map(lambda x: x["speed"], consumption_model)))
        consumption_energy_per_distance = (
            np.array(list(map(lambda x: x["energy_per_distance"], consumption_model)))
            * scale_factor
        )

        return TabularPowertrain(
            speed_units,
            distance_units,
            energy_units,
            consumption_speed,
            consumption_energy_per_distance,
        )

    def link_cost(self, link: LinkTraversal) -> float:
        """
        uses mph tabular value to calculate energy over a link


        :param link: the link to calculate energy over.
        :return: energy in units captured by self.energy_units
        """
        # convert kilometers per hour to whatever units are used by this powertrain
        link_speed = link.speed_kmph * get_unit_conversion(Unit.KMPH, self.speed_units)

        energy_per_distance = float(
            np.interp(
                link_speed,
                self.consumption_speed,
                self.consumption_energy_per_distance,
            )
        )
        # link distance is in kilometers
        link_distance = link.distance_km * get_unit_conversion(Unit.KILOMETERS, self.distance_units)
        energy = energy_per_distance * link_distance
        return energy

    def energy_cost(self, route: Route) -> float:
        return sum([self.link_cost(link) for link in route])
