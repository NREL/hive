from typing import NamedTuple, Optional

from hive.model.vehiclestate import VehicleState
from hive.model.energy.charger import Charger
from hive.util.typealiases import StationId, VehicleId, RequestId, GeoId


class Instruction(NamedTuple):
    vehicle_id: VehicleId
    action: VehicleState
    location: Optional[GeoId] = None
    request_id: Optional[RequestId] = None
    station_id: Optional[StationId] = None
    charger: Optional[Charger] = None

