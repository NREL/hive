from __future__ import annotations

from typing import (
    NamedTuple,
    Tuple,
    Optional,
    TypeVar,
    Dict,
    FrozenSet,
)

import h3
import immutables

from hive.util.typealiases import GeoId


class EntityUpdateResult(NamedTuple):
    entities: Optional[Dict] = None
    locations: Optional[Dict] = None
    search: Optional[Dict] = None


class DictOps:
    K = TypeVar('K')
    V = TypeVar('V')

    @classmethod
    def add_to_dict(cls, xs: immutables.Map[K, V], obj_id: K, obj: V) -> immutables.Map[K, V]:
        """
        updates Dicts for arbitrary keys and values
        performs a shallow copy and update, treating Dict as an immutable hash table


        :param xs:
        :param obj_id:
        :param obj:
        :return:
        """
        return xs.set(obj_id, obj)

    @classmethod
    def remove_from_dict(cls, xs: immutables.Map[K, V], obj_id: K) -> immutables.Map[K, V]:
        """
        updates Dicts for arbitrary keys and values
        performs a shallow copy and update, treating Dict as an immutable hash table


        :param xs:
        :param obj_id:
        :return:
        """
        return xs.delete(obj_id)

    @classmethod
    def merge_dicts(cls, old: immutables.Map[K, V], new: immutables.Map[K, V]) -> immutables.Map[K, V]:
        """
        merges two Dictionaries, replacing old kv pairs with new ones

        :param old: the old Dict
        :param new: the new Dict
        :return: a merged Dict
        """
        with old.mutate() as mutable:
            for k, v in new.items():
                mutable.set(k, v)
            tmp = mutable.finish()
        return tmp

    @classmethod
    def add_to_collection_dict(cls,
                               xs: immutables.Map[str, FrozenSet[V]],
                               collection_id: str,
                               obj_id: str) -> immutables.Map[str, FrozenSet[V]]:
        """
        updates Dicts that track collections of entities
        performs a shallow copy and update, treating Dict as an immutable hash table


        :param xs:
        :param collection_id:
        :param obj_id:
        :return:
        """
        ids_at_location = xs.get(collection_id, frozenset())
        updated_ids = ids_at_location.union([obj_id])
        return xs.set(collection_id, updated_ids)

    @classmethod
    def add_to_stack_dict(cls,
                          xs: immutables.Map[str, Tuple[V]],
                          collection_id: str,
                          obj: V) -> immutables.Map[str, Tuple[V]]:
        """
        updates Dicts that hold a stack of entities;
        note that the head of the tuple represents the top of the stack; elements always get inserted into the head;
        performs a shallow copy and update, treating Dict as an immutable hash table


        :param xs:
        :param collection_id:
        :param obj_id:
        :return:
        """
        stack = xs.get(collection_id, tuple())
        updated_stack = (obj,) + stack
        return xs.set(collection_id, updated_stack)

    @classmethod
    def pop_from_stack_dict(cls,
                            xs: immutables.Map[str, Tuple[V]],
                            collection_id: str,
                            ) -> Tuple[Optional[V], immutables.Map[str, Tuple[V]]]:
        """
        pops an element from the stack and returns it;
        note that the head of the tuple represents the top of the stack; popped elements come from the tuple head;
        performs a shallow copy and update, treating Dict as an immutable hash table


        :param xs:
        :param collection_id:
        :param obj_id:
        :return:
        """
        stack = xs.get(collection_id, tuple())
        if stack:
            obj, updated_stack = stack[0], stack[1:]
        else:
            obj, updated_stack = None, ()
        return obj, xs.set(collection_id, updated_stack)

    @classmethod
    def remove_from_collection_dict(cls,
                                    xs: immutables.Map[str, FrozenSet[V]],
                                    collection_id: str,
                                    obj_id: str) -> immutables.Map[str, FrozenSet[V]]:
        """
        updates Dicts that track collections of entities
        performs a shallow copy and update, treating Dict as an immutable hash table
        when a geoid has no ids after a remove, it deletes that geoid, to prevent geoid Dict memory leaks


        :param xs:
        :param collection_id:
        :param obj_id:
        :return:
        """
        ids_at_loc = xs.get(collection_id, frozenset())
        updated_ids = ids_at_loc.difference([obj_id])
        return xs.delete(collection_id) if len(updated_ids) == 0 else xs.set(collection_id, updated_ids)

    @classmethod
    def update_entity_dictionaries(cls,
                                   updated_entity: V,
                                   entities: immutables.Map[K, Tuple[V, ...]],
                                   locations: immutables.Map[GeoId, Tuple[K, ...]],
                                   search: immutables.Map[GeoId, Tuple[K, ...]],
                                   sim_h3_search_resolution: int) -> EntityUpdateResult:
        """
        updates all dictionaries related to an entity

        :param updated_entity: an entity which itself should have an "id" and a "geoid" attribute
        :param entities: the dictionary containing Entities by EntityId
        :param locations: the finest-resolution geoindex of this entity type
        :param search: the upper-level resolution geoindex
        :param sim_h3_search_resolution: the h3 resolution of the search collection
        :return: the updated dictionaries
        """
        old_entity = entities[updated_entity.id]
        entities_updated = DictOps.add_to_dict(entities, updated_entity.id, updated_entity)

        if old_entity.geoid == updated_entity.geoid:
            return EntityUpdateResult(
                entities=entities_updated
            )
        # unset from old geoid add add to new one
        locations_removed = DictOps.remove_from_collection_dict(locations,
                                                                old_entity.geoid,
                                                                old_entity.id)
        locations_updated = DictOps.add_to_collection_dict(locations_removed,
                                                           updated_entity.geoid,
                                                           updated_entity.id)

        old_search_geoid = h3.h3_to_parent(old_entity.geoid, sim_h3_search_resolution)
        updated_search_geoid = h3.h3_to_parent(updated_entity.geoid, sim_h3_search_resolution)

        if old_search_geoid == updated_search_geoid:
            # no update to search location
            return EntityUpdateResult(
                entities=entities_updated,
                locations=locations_updated
            )

        # update request search dict location
        search_removed = DictOps.remove_from_collection_dict(search,
                                                             old_search_geoid,
                                                             old_entity.id)
        search_updated = DictOps.add_to_collection_dict(search_removed,
                                                        updated_search_geoid,
                                                        updated_entity.id)

        return EntityUpdateResult(
            entities=entities_updated,
            locations=locations_updated,
            search=search_updated
        )
