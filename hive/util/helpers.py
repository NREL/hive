from __future__ import annotations

from copy import copy
from typing import Tuple, Dict, Optional, TypeVar

from hive.util.typealiases import Km, GeoId, Time
import haversine

from h3 import h3


class UnitOps:
    @classmethod
    def miles_to_km(cls, mph: float) -> float:
        return mph / 1.609

    @classmethod
    def km_to_miles(cls, kmph: float) -> float:
        return kmph * 1.609

    @classmethod
    def mph_to_km(cls, mph: float) -> float:
        return mph * 1.609

    @classmethod
    def km_to_mph(cls, kmph: float) -> float:
        return kmph / 1.609


class H3Ops:
    @classmethod
    def great_circle_distance(cls, a: GeoId, b: GeoId) -> Km:
        """
        computes the distance between two geoids
        :param a: one geoid
        :param b: another geoid
        :return: the haversine distance between the two GeoIds
        """
        a_coord = h3.h3_to_geo(a)
        b_coord = h3.h3_to_geo(b)
        distance_km = haversine.haversine(a_coord, b_coord)
        return distance_km

    @classmethod
    def point_along_link(cls, property_link: 'PropertyLink', available_time: Time) -> GeoId:
        """
        finds the GeoId which is some percentage between two GeoIds along a line
        :param property_link: the link we are finding a mid point along
        :param available_time: the amount of time to traverse
        :return: a GeoId along the Link
        """

        experienced_distance = available_time * property_link.speed
        percent_trip_experienced = experienced_distance / property_link.distance
        if percent_trip_experienced <= 0:
            return property_link.start
        elif percent_trip_experienced >= 1.0:
            return property_link.end
        else:
            # find the point along the line
            start = h3.h3_to_geo(property_link.start)
            end = h3.h3_to_geo(property_link.end)
            res = h3.h3_get_resolution(property_link.start)
            lat = start[0] + ((end[0] - start[0]) * percent_trip_experienced)
            lon = start[1] + ((end[1] - start[1]) * percent_trip_experienced)
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
        updated_ids = (obj_id,) + ids_at_location
        updated_dict.update([(obj_geoid, updated_ids)])
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
