from typing import Dict, FrozenSet

from hive.util.typealiases import RequestId, VehicleId, StationId, BaseId


class AtLocationResponse(Dict):
    """
    Wrapper for entities at a specific location.
    

    :param requests: requests at the location
    :type requests: :py:obj:`FrozenSet[RequestId, ...]`

    :param vehicles: vehicles at the location
    :type vehicles: :py:obj:`FrozenSet[VehicleId, ...]`

    :param station: station at the location
    :type station: :py:obj:`Optional[StationId]`

    :param base: base at the location
    :type base: :py:obj:`Optional[BaseId]`
    """
    requests: FrozenSet[RequestId]
    vehicles: FrozenSet[VehicleId]
    station: FrozenSet[StationId]
    base: FrozenSet[BaseId]
