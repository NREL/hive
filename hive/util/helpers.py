from typing import Tuple, Dict, Optional, TypeVar
from copy import copy


class TupleOps:
    T = TypeVar('T')

    @classmethod
    def remove(cls, xs: Tuple[T, ...], value: T) -> Optional[Tuple[T, ...]]:
        removed = tuple(filter(lambda x: x != value, xs))
        if len(removed) == len(xs):
            return None
        else:
            return removed


class DictOps:
    T = TypeVar('T')

    @classmethod
    def add_to_entity_dict(cls, xs: Dict[str, T], obj_id: str, obj: T) -> Dict[str, T]:
        """
        updates Dicts that contain entities by id
        performs a shallow copy and update, treating Dict as an immutable hash table
        :param xs:
        :param obj_id:
        :param obj:
        :return:
        """
        updated_dict = copy(xs)
        updated_dict.update([(obj_id, obj)])
        return updated_dict

    @classmethod
    def add_to_location_dict(cls,
                             xs: Dict[str, Tuple[T, ...]],
                             obj_geoid: str,
                             obj_id: str) -> Dict[str, Tuple[T, ...]]:
        """
        updates Dicts that track the geoid of entities
        performs a shallow copy and update, treating Dict as an immutable hash table
        :param xs:
        :param obj_geoid:
        :param obj_id:
        :return:
        """
        updated_dict = copy(xs)
        ids_at_location = updated_dict.get(obj_geoid, ())
        updated_dict.update([(obj_geoid, (obj_id,) + ids_at_location)])
        return updated_dict

    @classmethod
    def remove_from_entity_dict(cls, xs: Dict[str, T], obj_id: str) -> Dict[str, T]:
        """
        updates Dicts that contain entities by id
        performs a shallow copy and update, treating Dict as an immutable hash table
        :param xs:
        :param obj_id:
        :param obj:
        :return:
        """
        updated_dict = copy(xs)
        del updated_dict[obj_id]
        return updated_dict

    @classmethod
    def remove_from_location_dict(cls,
                                  xs: Dict[str, Tuple[T, ...]],
                                  obj_geoid: str,
                                  obj_id: str) -> Dict[str, Tuple[T, ...]]:
        """
        updates Dicts that track the geoid of entities
        performs a shallow copy and update, treating Dict as an immutable hash table
        when a geoid has no ids after a remove, it deletes that geoid, to prevent geoid Dict memory leaks
        :param xs:
        :param obj_geoid:
        :param obj_id:
        :return:
        """
        updated_dict = copy(xs)
        ids_at_loc = updated_dict[obj_geoid]
        updated_ids = TupleOps.remove(ids_at_loc, obj_id)
        if len(updated_ids) == 0:
            del updated_dict[obj_geoid]
        else:
            updated_dict[obj_geoid] = updated_ids
        return updated_dict
