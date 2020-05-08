import numpy as np
import yaml
from pkg_resources import resource_string

from hive.model.roadnetwork.link import Link
from hive.model.roadnetwork.routetraversal import Route
from hive.model.vehicle.mechatronics.powertrain.powertrain import Powertrain
from hive.util.units import KwH, KMPH_TO_MPH, KM_TO_MILE, WH_TO_KWH, WattHourPerMile


class TabularPowertrain(Powertrain):
    """
    builds a tabular, interpolated lookup model for energy consumption
    """

    def __init__(self, nominal_consupmption: WattHourPerMile):
        data = yaml.safe_load(resource_string('hive.resources.vehicles.mechatronics.powertrain', 'normalized.yaml'))

        # linear interpolation function approximation via these lookup values
        consumption_model = sorted(data['consumption_model'], key=lambda x: x['mph'])
        self._consumption_mph = np.array(list(map(lambda x: x['mph'], consumption_model)))  # miles/hour
        self._consumption_whmi = np.array(
            list(map(lambda x: x['whmi'], consumption_model))) * nominal_consupmption  # watthour/mile

    def link_cost(self, link: Link) -> KwH:
        """
        uses mph tabular value to calculate energy over a link

        :param link: the link to calculate energy over.
        :return: energy in kilowatt-hours
        """
        # link speed is in kilometer/hour
        link_speed_mph = link.speed_kmph * KMPH_TO_MPH  # mph
        watthour_per_mile = np.interp(link_speed_mph,
                                      self._consumption_mph,
                                      self._consumption_whmi)  # watthour / mile
        # link distance is in kilometers
        energy_wh = (watthour_per_mile * link.distance_km * KM_TO_MILE)  # watthour
        energy_kwh = energy_wh * WH_TO_KWH  # kilowatthour
        return energy_kwh

    def energy_cost(self, route: Route) -> KwH:
        return sum([self.link_cost(link) for link in route])
