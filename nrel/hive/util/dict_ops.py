from __future__ import annotations

from typing import (
    Any,
    Callable,
    Iterator,
    List,
    NamedTuple,
    Tuple,
    Optional,
    TypeVar,
    FrozenSet,
    TYPE_CHECKING,
    Hashable,
    Union,
)

import h3
import immutables

if TYPE_CHECKING:
    from nrel.hive.util.typealiases import EntityId, GeoId
    from nrel.hive.model.entity import Entity
    from _typeshed import SupportsRichComparison


class EntityUpdateResult(NamedTuple):
    entities: Optional[immutables.Map[EntityId, Entity]] = None
    locations: Optional[immutables.Map[GeoId, FrozenSet[EntityId]]] = None
    search: Optional[immutables.Map[GeoId, FrozenSet[EntityId]]] = None


class DictOps:
    K = TypeVar("K")
    V = TypeVar("V")

    @classmethod
    def iterate_vals(
        cls, xs: immutables.Map[K, V], key: Optional[Callable[[V], SupportsRichComparison]] = None
    ) -> Tuple[V, ...]:
        """
        helper function for iterating on Maps in HIVE which sorts values by key unless a key function
        is provided. for all stateful Map collections that are being iterated on in HIVE, we need
        to sort them _somehow_ to guarantee deterministic runs.

        if no key function is provided, the values are sorted by Map key. if a key function is provided,
        it takes the value type as input and returns a sortable value.

        :param xs: collection to iterate values of
        :type xs: immutables.Map[K, V]
        :return: values of xs, sorted by key
        :rtype: Tuple[V, ...]
        """
        # forcing ignore here after numerous attempts to set the bounds for K
        # to be "Union[SupportsRichComparison, Hashable]"
        if len(xs) == 0:
            return ()
        elif key is None:
            _, vs = zip(*sorted(xs.items(), key=lambda p: p[0]))  # type: ignore
            return vs
        else:
            vs = sorted(xs.values(), key=key)  # type: ignore
            return vs

    @classmethod
    def iterate_items(
        cls,
        xs: immutables.Map[K, V],
        key: Optional[Callable[[Tuple[K, V]], SupportsRichComparison]] = None,
    ) -> List[Tuple[K, V]]:
        """
        helper function for iterating on Maps in HIVE which sorts values by key unless a key function
        is provided. for all stateful Map collections that are being iterated on in HIVE, we need
        to sort them _somehow_ to guarantee deterministic runs.

        :param xs: collection to iterate values of
        :type xs: immutables.Map[K, V]
        :return: values of xs, sorted by key
        :rtype: Tuple[V, ...]
        """
        # forcing ignore here after numerous attempts to set the bounds for K
        # to be "Union[SupportsRichComparison, Hashable]"
        if len(xs) == 0:
            return []
        else:
            fn = key if key is not None else lambda p: p[0]  # type: ignore
            items = sorted(xs.items(), key=fn)  # type: ignore
            return items

    @classmethod
    def iterate_sim_coll(
        cls,
        collection: immutables.Map[K, V],
        filter_function: Optional[Callable[[V], bool]] = None,
        sort_key: Optional[Callable] = None,
    ) -> Tuple[V, ...]:
        """
        helper to iterate through a collection on the SimulationState with optional
        sort key function and filter function

        :param collection: collection on SimulationState
        :type collection: immutables.Map[K, V]
        :param filter_function: _description_, defaults to None
        :type filter_function: Optional[Callable[[V], bool]], optional
        :param sort_key: _description_, defaults to None
        :type sort_key: Optional[Callable], optional
        :return: _description_
        :rtype: Tuple[V, ...]
        """

        vals = DictOps.iterate_vals(collection, sort_key)
        if filter_function:
            return tuple(filter(filter_function, vals))
        else:
            return vals

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
    def merge_dicts(
        cls, old: immutables.Map[K, V], new: immutables.Map[K, V]
    ) -> immutables.Map[K, V]:
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
    def add_to_collection_dict(
        cls,
        xs: immutables.Map[str, FrozenSet[V]],
        collection_id: str,
        obj_id: V,
    ) -> immutables.Map[str, FrozenSet[V]]:
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
    def add_to_stack_dict(
        cls, xs: immutables.Map[str, Tuple[V, ...]], collection_id: str, obj: V
    ) -> immutables.Map[str, Tuple[V, ...]]:
        """
        updates Dicts that hold a stack of entities;
        note that the head of the tuple represents the top of the stack; elements always get inserted into the head;
        performs a shallow copy and update, treating Dict as an immutable hash table


        :param xs:
        :param collection_id:
        :param obj_id:
        :return:
        """
        stack = xs.get(collection_id, ())
        updated_stack = (obj,) + stack
        return xs.set(collection_id, updated_stack)

    @classmethod
    def pop_from_stack_dict(
        cls,
        xs: immutables.Map[str, Tuple[V, ...]],
        collection_id: str,
    ) -> Tuple[Optional[V], immutables.Map[str, Tuple[V, ...]]]:
        """
        pops an element from the stack and returns it;
        note that the head of the tuple represents the top of the stack; popped elements come from the tuple head;
        performs a shallow copy and update, treating Dict as an immutable hash table


        :param xs:
        :param collection_id:
        :param obj_id:
        :return:
        """
        stack = xs.get(collection_id, ())
        if stack:
            obj, updated_stack = stack[0], stack[1:]
        else:
            obj, updated_stack = None, ()
        return obj, xs.set(collection_id, updated_stack)

    @classmethod
    def remove_from_collection_dict(
        cls,
        xs: immutables.Map[str, FrozenSet[V]],
        collection_id: str,
        obj_id: str,
    ) -> immutables.Map[str, FrozenSet[V]]:
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
        return (
            xs.delete(collection_id)
            if len(updated_ids) == 0
            else xs.set(collection_id, updated_ids)
        )

    @classmethod
    def update_entity_dictionaries(
        cls,
        updated_entity: Entity,
        entities: immutables.Map[EntityId, Entity],
        locations: immutables.Map[GeoId, FrozenSet[EntityId]],
        search: immutables.Map[GeoId, FrozenSet[EntityId]],
        sim_h3_search_resolution: int,
    ) -> EntityUpdateResult:
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
            return EntityUpdateResult(entities=entities_updated)
        # unset from old geoid add add to new one
        locations_removed = DictOps.remove_from_collection_dict(
            locations, old_entity.geoid, old_entity.id
        )
        locations_updated = DictOps.add_to_collection_dict(
            locations_removed, updated_entity.geoid, updated_entity.id
        )

        old_search_geoid = h3.h3_to_parent(old_entity.geoid, sim_h3_search_resolution)
        updated_search_geoid = h3.h3_to_parent(updated_entity.geoid, sim_h3_search_resolution)

        if old_search_geoid == updated_search_geoid:
            # no update to search location
            return EntityUpdateResult(entities=entities_updated, locations=locations_updated)

        # update request search dict location
        search_removed = DictOps.remove_from_collection_dict(
            search, old_search_geoid, old_entity.id
        )
        search_updated = DictOps.add_to_collection_dict(
            search_removed, updated_search_geoid, updated_entity.id
        )

        return EntityUpdateResult(
            entities=entities_updated,
            locations=locations_updated,
            search=search_updated,
        )
