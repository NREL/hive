from typing import NamedTuple, Optional

from hive.model.vehiclestate import VehicleState
from hive.util.typealiases import VehicleId, RequestId, GeoId


class Instruction(NamedTuple):
    vehicle_id: VehicleId
    action: VehicleState
    location: Optional[GeoId]
    request: Optional[RequestId]

