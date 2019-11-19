from typing import Dict, TypedDict, List, Tuple

from hive.model.powertrain.powertrain import Powertrain
from hive.roadnetwork.link import Link
from hive.roadnetwork.roadnetwork import RoadNetwork
from hive.roadnetwork.route import Route
from hive.roadnetwork.routesegment import RouteSegment
from hive.util.typealiases import KwH, PowertrainId
import numpy as np


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

    def route_energy_cost(self, route: Route, road_network: RoadNetwork) -> KwH:
        pass

    def segment_energy_cost(self, segment: RouteSegment, road_network: RoadNetwork) -> KwH:
        pass

    def start_link_energy_cost(self, link: Link, road_network: RoadNetwork) -> KwH:
        pass

    def end_link_energy_cost(self, link: Link, road_network: RoadNetwork) -> KwH:
        pass

    def link_energy_cost(self, link: Link, road_network: RoadNetwork) -> KwH:
        speed = road_network.get_link_speed(link.position)
        watt_per_mile = np.interp(speed, self._consumption_mph, self._consumption_whmi)
        raise NotImplementedError("do something with watt_per_mile")

