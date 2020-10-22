from typing import NamedTuple

from hive.util.typealiases import ScheduleId, VehicleId, BaseId


class HumanDriverAttributes(NamedTuple):
    """
    the set of attributes which persist for a human driver
    """
    vehicle_id: VehicleId
    schedule_id: ScheduleId
    home_base_id: BaseId
    # start_time: SimTime ?
    # agency_ids: frozenset[AgencyId] ?




