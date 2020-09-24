from typing import NamedTuple

from hive.util.typealiases import ScheduleId


class HumanDriverAttributes(NamedTuple):
    """
    the set of attributes which persist for a human driver
    """
    schedule_id: ScheduleId
    # home_base: BaseId
    # start_time: SimTime ?
    # agency_ids: frozenset[AgencyId] ?
    pass




