from typing import Dict, TypedDict, List

from hive.model.powertrain.powertrain import Powertrain
from hive.roadnetwork.link import Link
from hive.roadnetwork.route import Route
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
        self.id = data['name']

        consumption_model = data['consumption_model']
        self._consumption_mph = list(map(lambda x: x['mph'], consumption_model))
        self._consumption_whmi = list(map(lambda x: x['whmi'], consumption_model))

        charging_model = data['charging_model']
        self._charging_soc = list(map(lambda x: x['soc'], charging_model))
        self._charging_c_kw = list(map(lambda x: x['kw'], charging_model))

        pass

    def get_id(self) -> PowertrainId:
        return self.id

    def route_fuel_cost(self, route: Route) -> KwH:
        pass

    def route_step_fuel_cost(self, route_step: Link) -> KwH:
        pass

