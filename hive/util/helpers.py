from __future__ import annotations

from abc import abstractmethod, ABC
from math import radians, cos, sin, asin, sqrt, ceil
from typing import Dict, Optional, TypeVar, Callable, TYPE_CHECKING, NamedTuple

import immutables
from h3 import h3

from hive.util.exception import H3Error
from hive.util.typealiases import *
from hive.util.units import Kilometers, Seconds, SECONDS_TO_HOURS

if TYPE_CHECKING:
    from hive.model.roadnetwork.link import Link

Entity = TypeVar('Entity')
EntityId = TypeVar('EntityId')

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


class SwitchCase(ABC):

    @abstractmethod
    def _default(self, arguments: Arguments) -> Result:
        """
        called when "key" does not exist in the SwitchCase

        :param arguments: the arguments to pass in the default case
        :return:
        """

    case_statement: Dict[Key, Callable[[Arguments], Result]] = {}

    @classmethod
    def switch(cls, case, payload: Arguments) -> Result:
        return cls.case_statement.get(case, cls._default)(cls, payload)


class H3Ops:
    @classmethod
    def nearest_entity(cls,
                       geoid: GeoId,
                       entities: immutables.Map[EntityId, Entity],
                       entity_search: immutables.Map[GeoId, Tuple[EntityId, ...]],
                       sim_h3_search_resolution: int,
                       is_valid: Callable[[Entity], bool] = lambda x: True,
                       max_distance_km: Kilometers = 10  # kilometers
                       ) -> Optional[Entity]:
        """
        returns the closest entity to the given geoid. In the case of a tie, the first entity encountered is returned.
        invariant: the Entity has a geoid field (Entity.geoid)
        :param geoid: the search origin
        :param entities: a collection of a certain type of entity, by Id type
        :param entity_search: the location of objects of this entity type, registered at a high-level grid resolution
        :param sim_h3_search_resolution: the h3 resolution of the entity_search collection
        :param is_valid: a function used to filter valid search results, such as checking stations for charger availability
        :param k: the number of concentric rings to check in the high-level search
        :param max_distance_km: the maximum distance a result can be from the search origin

        :return: the nearest entity, or, None if not found within the constraints
        """
        geoid_res = h3.h3_get_resolution(geoid)
        if geoid_res < sim_h3_search_resolution:
            raise H3Error('search resolution must be less than geoid resolution')

        k_dist_km = h3.edge_length(sim_h3_search_resolution, unit='km') * 2  # kilometers
        max_k = ceil(max_distance_km / k_dist_km)
        search_geoid = h3.h3_to_parent(geoid, sim_h3_search_resolution)

        def _search(current_k: int = 0) -> Optional[Entity]:
            if current_k > max_k:
                # There are no entities in any of the rings.
                return None
            else:
                # get the kth ring
                ring = h3.k_ring(search_geoid, current_k)

                # get all entities in this ring
                found = (entity for cell in ring
                         for entity in cls.get_entities_at_cell(cell, entity_search, entities))

                best_dist_km = 1000000
                best_entity = None

                count = 0
                for entity in found:
                    dist_km = cls.great_circle_distance(geoid, entity.geoid)
                    if is_valid(entity) and dist_km < best_dist_km:
                        best_dist_km = dist_km
                        best_entity = entity
                    count += 1

                if best_entity is not None:
                    # print(f"ring search depth {current_k} found {count} agents, best agent at dist {best_dist} km")
                    return best_entity
                else:
                    return _search(current_k + 1)

        return _search()

    @classmethod
    def get_entities_at_cell(cls,
                             search_cell: GeoId,
                             entity_search: immutables.Map[GeoId, Tuple[EntityId, ...]],
                             entities: immutables.Map[EntityId, Entity]) -> Tuple[Entity, ...]:
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
                         for entity_id in locations_at_cell)

    @classmethod
    def nearest_entity_point_to_point(cls,
                                      geoid: GeoId,
                                      entities: Dict[EntityId, Entity],
                                      entity_locations: Dict[GeoId, Tuple[EntityId, ...]],
                                      is_valid: Callable = lambda x: True,
                                      ) -> Optional[Entity]:
        """
        A nearest neighbor search that scans all entities and returns the one with the lowest distance to the geoid.

        :param geoid: GeoId to match to
        :param entities: Entities to search over
        :param entity_locations: Location of entities
        :param is_valid: Optional function to filter for valid entities
        :return: an optional entity if found
        """

        best_dist_km = 1000000
        best_e = None
        for e_geoid, e_ids in entity_locations.items():
            dist_km = cls.great_circle_distance(geoid, e_geoid)
            for e_id in e_ids:
                if e_id not in entities:
                    continue
                e = entities[e_id]
                if dist_km < best_dist_km and is_valid(e):
                    best_dist_km = dist_km
                    best_e = e

        return best_e

    @classmethod
    def great_circle_distance(cls, a: GeoId, b: GeoId) -> Kilometers:
        """
        computes the distance between two geoids

        :param a: one geoid
        :param b: another geoid
        :return: the haversine distance between the two GeoIds
        """
        avg_earth_radius_km = 6371

        lat1, lon1 = h3.h3_to_geo(a)
        lat2, lon2 = h3.h3_to_geo(b)

        # convert all latitudes/longitudes from decimal degrees to radians
        lat1, lon1, lat2, lon2 = map(radians, (lat1, lon1, lat2, lon2))

        # calculate haversine
        lat = lat2 - lat1
        lon = lon2 - lon1
        d = sin(lat * 0.5) ** 2 + cos(lat1) * cos(lat2) * sin(lon * 0.5) ** 2

        return 2 * avg_earth_radius_km * asin(sqrt(d))

    @classmethod
    def point_along_link(cls, link: Link, available_time_seconds: Seconds) -> GeoId:
        """
        finds the GeoId which is some percentage between two GeoIds along a line

        :param available_time_seconds: the amount of time to traverse
        :param property_link: the link we are finding a mid point along
        :return: a GeoId along the Link
        """

        threshold = 0.001
        experienced_distance_km = (available_time_seconds * SECONDS_TO_HOURS) * link.speed_kmph
        ratio_trip_experienced = experienced_distance_km / link.distance_km
        if ratio_trip_experienced < (0 + threshold):
            return link.start
        elif (1 - threshold) < ratio_trip_experienced:
            return link.end
        else:
            # find the point along the line
            start = h3.h3_to_geo(link.start)
            end = h3.h3_to_geo(link.end)
            res = h3.h3_get_resolution(link.start)
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
    def add_to_location_dict(cls,
                             xs: immutables.Map[str, Tuple[V, ...]],
                             obj_geoid: str,
                             obj_id: str) -> immutables.Map[str, Tuple[V, ...]]:
        """
        updates Dicts that track the geoid of entities
        performs a shallow copy and update, treating Dict as an immutable hash table

        :param xs:
        :param obj_geoid:
        :param obj_id:
        :return:
        """
        ids_at_location = xs.get(obj_geoid, ())
        updated_ids = (obj_id,) + ids_at_location
        return xs.set(obj_geoid, updated_ids)

    @classmethod
    def remove_from_location_dict(cls,
                                  xs: immutables.Map[str, Tuple[V, ...]],
                                  obj_geoid: str,
                                  obj_id: str) -> immutables.Map[str, Tuple[V, ...]]:
        """
        updates Dicts that track the geoid of entities
        performs a shallow copy and update, treating Dict as an immutable hash table
        when a geoid has no ids after a remove, it deletes that geoid, to prevent geoid Dict memory leaks

        :param xs:
        :param obj_geoid:
        :param obj_id:
        :return:
        """
        ids_at_loc = xs.get(obj_geoid, ())
        updated_ids = TupleOps.remove(ids_at_loc, obj_id)
        return xs.delete(obj_geoid) if len(updated_ids) == 0 else xs.set(obj_geoid, updated_ids)

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
        locations_removed = DictOps.remove_from_location_dict(locations,
                                                              old_entity.geoid,
                                                              old_entity.id)
        locations_updated = DictOps.add_to_location_dict(locations_removed,
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
        search_removed = DictOps.remove_from_location_dict(search,
                                                           old_search_geoid,
                                                           old_entity.id)
        search_updated = DictOps.add_to_location_dict(search_removed,
                                                      updated_search_geoid,
                                                      updated_entity.id)

        return EntityUpdateResult(
            entities=entities_updated,
            locations=locations_updated,
            search=search_updated
        )
