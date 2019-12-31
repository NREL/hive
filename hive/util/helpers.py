from __future__ import annotations

from abc import abstractmethod, ABC
from copy import copy
from typing import Dict, Optional, TypeVar, Callable, TYPE_CHECKING, FrozenSet
import functools as ft

from hive.util.typealiases import *
from hive.util.units import unit, km, h

import haversine

from h3 import h3
from math import ceil

if TYPE_CHECKING:
    from hive.model.roadnetwork.property_link import PropertyLink


class SwitchCase(ABC):
    Key = TypeVar('Key')
    """
    the type used to switch off of
    """

    Arguments = TypeVar('Arguments')
    """
    the type of the arguments fed to the inner switch clause
    """

    Result = TypeVar('Result')
    """
    the type returned from the SwitchCase (can be "Any")
    """

    @abstractmethod
    def _default(self, arguments: Arguments) -> Result:
        """
        called when "key" does not exist in the SwitchCase
        :param arguments: the arguments to pass in the default case
        :return:
        """
        pass

    case_statement: Dict[Key, Callable[[Arguments], Result]] = {}

    @classmethod
    def switch(cls, case, payload: Arguments) -> Result:
        return cls.case_statement.get(case, cls._default)(cls, payload)


class H3Ops:
    Entity = TypeVar('Entity')
    EntityId = TypeVar('EntityId')

    @classmethod
    def nearest_entity(cls,
                       geoid: GeoId,
                       entities: Dict[EntityId, Entity],
                       entity_search: Dict[GeoId, FrozenSet[GeoId, ...]],
                       entity_locations: Dict[GeoId, Tuple[EntityId, ...]],
                       sim_h3_search_resolution: int,
                       is_valid: Callable[[Entity], bool] = lambda x: True,
                       max_distance_km: km = 100 * unit.kilometers
                       ) -> Optional[Entity]:
        """
        returns the closest entity to the given geoid. In the case of a tie, the first entity encountered is returned.
        invariant: the Entity has a geoid field (Entity.geoid)
        :param geoid: the search origin
        :param entities: a collection of a certain type of entity, by Id type
        :param entity_search: the location of objects of this entity type, registered at a high-level grid resolution
        :param entity_locations: the location of objects of this entity type at the finest grid resolution
        :param sim_h3_search_resolution: the h3 resolution of the entity_search collection
        :param is_valid: a function used to filter valid search results, such as checking stations for charger availability
        :param k: the number of concentric rings to check in the high-level search
        :param max_distance_km: the maximum distance a result can be from the search origin

        :return: the nearest entity, or, None if not found within the constraints
        """

        k_dist_km = h3.edge_length(sim_h3_search_resolution, unit='km') * 2 * unit.kilometers
        max_k = ceil(max_distance_km.magnitude / k_dist_km.magnitude)
        search_geoid = h3.h3_to_parent(geoid, sim_h3_search_resolution)

        def _search(current_k: int = 0) -> Optional['Entity']:
            if current_k > max_k:
                # There are no entities in any of the rings.
                return None
            else:
                # get the kth ring
                ring = h3.k_ring(search_geoid, current_k)

                # get all entities in this ring
                found = (entity for cell in ring
                         for entity in cls.get_entities_at_cell(cell, entity_search, entity_locations, entities))

                best_dist = 1000000 * unit.kilometers
                best_entity = None

                for entity in found:
                    dist = cls.great_circle_distance(geoid, entity.geoid)
                    if is_valid(entity) and dist < best_dist:
                        best_dist = dist
                        best_entity = entity

                if best_entity is not None:
                    return best_entity
                else:
                    return _search(current_k + 1)

        return _search()

    @classmethod
    def get_entities_at_cell(cls,
                             search_cell: GeoId,
                             entity_search: Dict[GeoId, FrozenSet[GeoId, ...]],
                             entity_locations: Dict[GeoId, Tuple[EntityId, ...]],
                             entities: Dict[EntityId, Entity]) -> Tuple[Entity, ...]:
        """
        gives us entities within a high-level search cell

        :param search_cell: the search-level h3 position we are looking at
        :param entity_search: the upper-level search collection for this entity type
        :param entity_locations: the lower-level location collection
        :param entities: the actual entities
        :return: any entities which are located at this search-level cell
        """
        locations_at_cell = entity_search.get(search_cell)
        if locations_at_cell is None:
            return ()
        else:
            return tuple(entities[entity_id]
                         for loc in locations_at_cell
                         for entity_id in entity_locations[loc])

    @classmethod
    def nearest_entity_point_to_point(cls,
                                      geoid: GeoId,
                                      entities: Dict[EntityId, Entity],
                                      entity_locations: Dict[GeoId, Tuple[EntityId, ...]],
                                      is_valid: Callable = lambda x: True,
                                      ) -> Optional[Entity]:

        best_dist = 1000000 * unit.kilometers
        best_e = None
        for e_geoid, e_ids in entity_locations.items():
            dist = cls.great_circle_distance(geoid, e_geoid)
            for e_id in e_ids:
                if e_id not in entities:
                    continue
                e = entities[e_id]
                if dist < best_dist and is_valid(e):
                    best_dist = dist
                    best_e = e

        return best_e

    @classmethod
    def great_circle_distance(cls, a: GeoId, b: GeoId) -> km:
        """
        computes the distance between two geoids
        :param a: one geoid
        :param b: another geoid
        :return: the haversine distance between the two GeoIds
        """
        a_coord = h3.h3_to_geo(a)
        b_coord = h3.h3_to_geo(b)
        distance_km = haversine.haversine(a_coord, b_coord) * unit.kilometer
        return distance_km

    @classmethod
    def point_along_link(cls, property_link: PropertyLink, available_time: h) -> GeoId:
        """
        finds the GeoId which is some percentage between two GeoIds along a line
        :param property_link: the link we are finding a mid point along
        :param available_time: the amount of time to traverse
        :return: a GeoId along the Link
        """

        threshold = 0.001
        experienced_distance = available_time * property_link.speed
        ratio_trip_experienced = experienced_distance / property_link.distance
        if ratio_trip_experienced < (0 + threshold):
            return property_link.start
        elif (1 - threshold) < ratio_trip_experienced:
            return property_link.end
        else:
            # find the point along the line
            start = h3.h3_to_geo(property_link.start)
            end = h3.h3_to_geo(property_link.end)
            res = h3.h3_get_resolution(property_link.start)
            lat = start[0] + ((end[0] - start[0]) * ratio_trip_experienced)
            lon = start[1] + ((end[1] - start[1]) * ratio_trip_experienced)
            return h3.geo_to_h3(lat, lon, res)


class TupleOps:
    T = TypeVar('T')

    @classmethod
    def remove(cls, xs: Tuple[T, ...], value: T) -> Tuple[T, ...]:
        removed = tuple(filter(lambda x: x != value, xs))
        if len(removed) == len(xs):
            return ()
        else:
            return removed

    @classmethod
    def head(cls, xs: Tuple[T, ...]) -> T:
        if len(xs) == 0:
            raise IndexError("called head on empty Tuple")
        else:
            return xs[0]

    @classmethod
    def head_optional(cls, xs: Tuple[T, ...]) -> Optional[T]:
        if len(xs) == 0:
            return None
        else:
            return xs[0]

    @classmethod
    def last(cls, xs: Tuple[T, ...]) -> T:
        if len(xs) == 0:
            raise IndexError("called last on empty Tuple")
        else:
            return xs[-1]

    @classmethod
    def last_optional(cls, xs: Tuple[T, ...]) -> Optional[T]:
        if len(xs) == 0:
            return None
        else:
            return xs[-1]

    @classmethod
    def head_tail(cls, tup: Tuple[T, ...]):
        if not tup:
            raise IndexError("called head_tail on empty Tuple")
        elif len(tup) == 1:
            return tup[0], ()
        else:
            return tup[0], tup[1:]


class DictOps:
    K = TypeVar('K')
    V = TypeVar('V')

    @classmethod
    def add_to_dict(cls, xs: Dict[K, V], obj_id: K, obj: V) -> Dict[K, V]:
        """
        updates Dicts for arbitrary keys and values
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
    def remove_from_dict(cls, xs: Dict[K, V], obj_id: K) -> Dict[K, V]:
        """
        updates Dicts for arbitrary keys and values
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
    def add_to_location_dict(cls,
                             xs: Dict[str, Tuple[V, ...]],
                             obj_geoid: str,
                             obj_id: str) -> Dict[str, Tuple[V, ...]]:
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
        updated_ids = (obj_id,) + ids_at_location
        updated_dict.update([(obj_geoid, updated_ids)])
        return updated_dict

    @classmethod
    def remove_from_location_dict(cls,
                                  xs: Dict[str, Tuple[V, ...]],
                                  obj_geoid: str,
                                  obj_id: str) -> Dict[str, Tuple[V, ...]]:
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

    @classmethod
    def add_to_search_dict(cls,
                           xs: Dict[GeoId, FrozenSet[GeoId, ...]],
                           location_geoid: GeoId,
                           sim_h3_search_resolution: int) -> Dict[GeoId, FrozenSet[GeoId, ...]]:
        """
        updates Dicts used in the bi-level nearest neighbors search
        performs a shallow copy and update, treating Dict as an immutable hash table
        only keeps one copy of the lower-level key per upper-level key
        :param xs: the collection we are adding to
        :param location_geoid: the lower-level geo index used to store exact entity locations
        :param sim_h3_search_resolution:
        :return: the updated dictionary
        """
        updated_dict = copy(xs)
        search_geoid = h3.h3_to_parent(location_geoid, sim_h3_search_resolution)
        ids_at_location = updated_dict.get(search_geoid, frozenset())
        updated_ids = ids_at_location.union([location_geoid])
        updated_dict.update([(search_geoid, updated_ids)])
        return updated_dict

    @classmethod
    def remove_from_search_dict(cls,
                                locations: Dict[GeoId, Tuple[K, ...]],
                                search: Dict[GeoId, FrozenSet[GeoId, ...]],
                                location_geoid: GeoId,
                                sim_h3_search_resolution: int) -> Dict[GeoId, FrozenSet[GeoId, ...]]:
        """
        updates Dicts used in the bi-level nearest neighbors search
        performs a shallow copy and update, treating Dict as an immutable hash table
        when a geoid has no ids after a remove, it deletes that geoid, to prevent geoid Dict memory leaks
        :param locations: the actual locations, used to identify if other entities are still at this location
        :param search: the search dict we are updating
        :param location_geoid:
        :param sim_h3_search_resolution:
        :return:
        """
        other_entities_at_old_search = locations.get(location_geoid) and len(locations.get(location_geoid)) > 1
        if other_entities_at_old_search:
            return search
        else:
            search_geoid = h3.h3_to_parent(location_geoid, sim_h3_search_resolution)
            updated_dict = copy(search)
            ids_at_loc = updated_dict[search_geoid]
            updated_ids = ids_at_loc.difference([location_geoid])
            if len(updated_ids) == 0:
                del updated_dict[search_geoid]
            else:
                updated_dict[search_geoid] = updated_ids
            return updated_dict

    @classmethod
    def update_search_dict(cls,
                           locations: Dict[GeoId, Tuple[K, ...]],
                           search: Dict[GeoId, FrozenSet[GeoId, ...]],
                           old_location_geoid: GeoId,
                           new_location_geoid: GeoId,
                           sim_h3_search_resolution: int) -> Dict[GeoId, FrozenSet[GeoId, ...]]:
        """
        checks if we are updating the location_geoid or removing it
        checks to see if any entities are still at a location before removing them
        from the upper-level lookup
        :param locations: locations *before* executing a remove_from_location_dict operation
        :param search: the search lookup we are modifying
        :param old_location_geoid:
        :param new_location_geoid:
        :param sim_h3_search_resolution: the resolution that the upper-level search locations are stored at
        :return: the updated search collection, or, no modification if
        other entities are still located at that location geoid
        """

        remove_old_search = DictOps.remove_from_search_dict(
            locations,
            search,
            old_location_geoid,
            sim_h3_search_resolution
        )
        add_new_search = DictOps.add_to_search_dict(
            remove_old_search,
            new_location_geoid,
            sim_h3_search_resolution
        )
        return add_new_search
