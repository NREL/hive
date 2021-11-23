from __future__ import annotations

import yaml
import immutables
from typing import TYPE_CHECKING, FrozenSet

if TYPE_CHECKING:
    from hive.util.typealiases import EntityId, MembershipMap


def process_fleet_file(fleet_file: str, entity_type: str) -> MembershipMap:
    """
    creates an immutable map that contains all of the fleet ids associated with the appropriate entity ids

    :param fleet_file: the file to load memberships from
    :param entity_type: the category the entity falls under, such as vehicles, bases, or stations
    :return: an immutable map mapping all entity ids with the appropriate memberships
    :raises Exception: from KEYErrors parsing the fleets file
        """
    fleet_id_map = immutables.Map()
    fleet_id_map_mutation = fleet_id_map.mutate()

    with open(fleet_file) as f:
        config_dict = yaml.safe_load(f)

        for fleet_id in config_dict:
            for entity_id in config_dict[fleet_id][entity_type]:
                if entity_id in fleet_id_map_mutation:
                    fleet_id_map_mutation[entity_id] = fleet_id_map_mutation[entity_id] + (fleet_id,)
                else:
                    fleet_id_map_mutation.set(entity_id, (fleet_id,))
        fleet_id_map = fleet_id_map_mutation.finish()
    return fleet_id_map


def read_fleet_ids_from_file(fleet_file: str) -> FrozenSet[EntityId]:
    """

    :param fleet_file: the file containing fleet information
    :return: the list of base-level keys in the fleet file, which should be fleet ids
    :raises: IOError if fleet_file does not exist or is not a yaml file
    """
    try:
        with open(fleet_file) as f:
            fleet_dict = yaml.safe_load(f)
        result = frozenset(fleet_dict.keys())
        return result
    except Exception as e:
        raise IOError(f"failed reading fleet ids from fleet file {fleet_file}") from e
