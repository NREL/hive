from typing import Dict, Tuple, Optional

from hive.util.typealiases import RequestId, VehicleId, StationId, BaseId


class AtLocationResponse(Dict):
    """
    Wrapper for entities at a specific location.
    
    :param requests: requests at the location
    :type requests: :py:obj:`Tuple[RequestId, ...]`
    :param vehicles: vehicles at the location
    :type vehicles: :py:obj:`Tuple[VehicleId, ...]`
    :param station: station at the location
    :type station: :py:obj:`Optional[StationId]`
    :param base: base at the location
    :type base: :py:obj:`Optional[BaseId]`
    """
    requests: Tuple[RequestId, ...]
    vehicles: Tuple[VehicleId, ...]
    station: Optional[StationId]
    base: Optional[BaseId]
