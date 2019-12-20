from __future__ import annotations

from abc import abstractmethod, ABC
from copy import copy
from typing import Dict, Optional, TypeVar, Callable, TYPE_CHECKING

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
                       entity_locations: Dict[GeoId, Tuple[EntityId, ...]],
                       is_valid: Callable = lambda x: True,
                       k: int = 0,
                       max_distance_km: km = 1 * unit.kilometers,
                       ) -> Optional[Entity]:
        """
        returns the closest entity to the given geoid. In the case of a tie, the first entity encountered is returned.

        :param geoid: Geoid to match to.
        :param entities: Entities to search over.
        :param entity_locations: Location of the entities
        :param is_valid: Optional function to filter for valid entities.
        :param k: the size of the k-ring
        :param max_distance_km: the maximum distance in kilometers to search over
        :return: an optional entity if found
        """
        resolution = h3.h3_get_resolution(geoid)
        k_dist_km = h3.edge_length(resolution, unit='km') * 2 * unit.kilometers
        max_k = ceil(max_distance_km.magnitude / k_dist_km.magnitude)

        if k > max_k:
            # There are no entities in any of the rings.
            return None

        ring = h3.k_ring_distances(geoid, k)[k]

        for gid in ring:
            if gid in entity_locations:
                entities_at_location = entity_locations[gid]
                if entities_at_location:
                    for entity_id in entities_at_location:
                        entity = entities[entity_id]
                        if is_valid(entity):
                            return entity

        return cls.nearest_entity(geoid, entities, entity_locations, is_valid, k + 1, max_distance_km)

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
    def remove(cls, xs: Tuple[T, ...], value: T) -> Optional[Tuple[T, ...]]:
        removed = tuple(filter(lambda x: x != value, xs))
        if len(removed) == len(xs):
            return None
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


