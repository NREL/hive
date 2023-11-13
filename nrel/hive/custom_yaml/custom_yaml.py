import logging
from pathlib import PurePath
from typing import Any, Union

import yaml

from nrel.hive.dispatcher.instruction_generator.charging_search_type import ChargingSearchType
from nrel.hive.model.sim_time import SimTime
from nrel.hive.model.vehicle.schedules.schedule_type import ScheduleType
from nrel.hive.reporting.report_type import ReportType

log = logging.getLogger(__name__)

custom_yaml = yaml

# This tag is not written to the file during serialization because interpretation is implicit during YAML deserialization.
YAML_STR_TAG = "tag:yaml.org,2002:str"


# Handling stdlib objects that should be represented by list(obj).
# Prefer to handle classes within their own definition and then register below.
def convert_to_unsorted_list(dumper: custom_yaml.Dumper, obj: tuple):
    """Patches PyYAML representation for an object so that it is treated as a YAML list. Avoids an explicit YAML tag."""
    return dumper.represent_list(list(obj))


custom_yaml.add_representer(data_type=tuple, representer=convert_to_unsorted_list)


# Handling stdlib objects that should be represented by sorted(list(obj)).
# Prefer to handle classes within their own definition and then register below.
def convert_to_sorted_list(dumper: custom_yaml.Dumper, obj: set):
    """Patches PyYAML representation for an object so that it is treated as a YAML list. Avoids an explicit YAML tag."""
    return dumper.represent_list(sorted(list(obj)))


custom_yaml.add_representer(data_type=set, representer=convert_to_sorted_list)


# Handling stdlib objects that should be represented as str(obj).
# Prefer to handle classes within their own definition and then register below.
def convert_to_str(dumper: custom_yaml.Dumper, path: PurePath):
    """Patches PyYAML representation for an object so that it is treated as a YAML str. Avoids an explicit YAML tag."""
    return dumper.represent_scalar(tag=YAML_STR_TAG, value=str(path))


custom_yaml.add_multi_representer(data_type=PurePath, multi_representer=convert_to_str)


# Registering explicit/specific representers that are kept withing their classes.
custom_yaml.add_representer(
    data_type=ChargingSearchType, representer=ChargingSearchType.yaml_representer
)
custom_yaml.add_representer(data_type=ReportType, representer=ReportType.yaml_representer)
custom_yaml.add_representer(data_type=ScheduleType, representer=ScheduleType.yaml_representer)
custom_yaml.add_representer(data_type=SimTime, representer=SimTime.yaml_representer)


# Fallback to str() representation for any child of `object`.
# Raise a warning to alert the user that implicit serialization was done.
# Does not appear to work for built-in types that PyYaml has special serializers for.
def generic_representer(dumper: custom_yaml.Dumper, obj: object):
    """Serializes arbitrary objects to strs."""
    log.warning(f"{obj.__class__} object was implicity serialized with `str(obj)`.")
    tag = YAML_STR_TAG
    val = str(obj)
    return dumper.represent_scalar(tag=tag, value=val)


custom_yaml.add_multi_representer(data_type=object, multi_representer=generic_representer)
