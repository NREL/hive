from typing import Tuple, Dict, FrozenSet

import yaml
import immutables

from hive.util.helpers import DictOps


def process_fleet_file(fleet_file: str, entity_type: str) -> immutables.Map[str, FrozenSet[str]]:
    """
    creates a dictionary that contains all of the fleet ids associated with the appropriate entity ids

    :param fleet_file: the file to load memberships from
    :param entity_type: the category the entity falls under, such as vehicles, bases, or stations
    :return: a dictionary mapping all entity ids with the appropriate memberships
    :raises Exception: from KEYErrors parsing the fleets file
        """
    fleet_id_dict = immutables.Map()
    with open(fleet_file) as f:
        config_dict = yaml.safe_load(f)
        for fleet_id in config_dict:
            for entity_id in config_dict[fleet_id][entity_type]:
                if entity_id in fleet_id_dict:
                    fleet_id_dict = DictOps.add_to_collection_dict(fleet_id_dict, entity_id, fleet_id)
                else:
                    fleet_id_dict = DictOps.add_to_dict(fleet_id_dict, entity_id, frozenset([fleet_id]))
    return fleet_id_dict
