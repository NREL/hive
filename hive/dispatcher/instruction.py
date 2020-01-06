from typing import NamedTuple, Optional

from hive.model.vehiclestate import VehicleState
from hive.model.energy.charger import Charger
from hive.util.typealiases import StationId, VehicleId, RequestId, GeoId


class Instruction(NamedTuple):
    """
    Tuple that represents instructions for vehicles. These instructions have optional attributes based on their nature.

    :param vehicle_id: The id of the vehicles to apply this instruction to.
    :type vehicle_id: :py:obj:`VehicleId`
    :param action: The action. Represented by a vehicle state that the vehicle should transition to.
    :type action: :py:obj:`VehicleState`
    :param location: Geoid of the destination if the instruction involves relocating to an arbitrary location.
    :type location: :py:obj:`GeoId`
    :param request_id: Id of the request if the instruction involves dispatching or servicing a trip.
    :type request_id: :py:obj:`RequestId`
    :param station_id: Id of the station if the instruction involves dispatching or charging at a station.
    :type station_id: :py:obj:`StationId`
    :param charger: Type of charger if the instruction involves dispatching or charging at a station.
    :type charger: :py:obj:`Charger`
    """
    vehicle_id: VehicleId
    action: VehicleState
    location: Optional[GeoId] = None
    request_id: Optional[RequestId] = None
    station_id: Optional[StationId] = None
    charger: Optional[Charger] = None

