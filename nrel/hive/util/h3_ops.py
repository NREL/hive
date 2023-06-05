from __future__ import annotations

from typing import Any, Dict, Optional, TYPE_CHECKING, FrozenSet, Iterable, Callable, Tuple

import h3
import immutables
from math import radians, cos, sin, asin, sqrt, ceil
from nrel.hive.util.dict_ops import DictOps

from nrel.hive.util.exception import H3Error
from nrel.hive.util.typealiases import EntityId, GeoId
from nrel.hive.util.units import Kilometers, Seconds, SECONDS_TO_HOURS

if TYPE_CHECKING:
    from nrel.hive.model.entity import Entity
    from nrel.hive.model.roadnetwork.linktraversal import LinkTraversal


class H3Ops:
    @classmethod
    def nearest_entity_by_great_circle_distance(
        cls,
        geoid: GeoId,
        entities: Iterable[Entity],
        entity_search: immutables.Map[GeoId, FrozenSet[EntityId]],
        sim_h3_search_resolution: int,
        is_valid: Callable[[Any], bool] = lambda x: True,
        max_search_distance_km: Kilometers = 10,  # kilometers
    ) -> Optional[Entity]:
        """
        returns the closest entity to the given geoid. In the case of a tie, the first entity encountered is returned.
        invariant: the Entity has a geoid field (Entity.geoid)


        :param geoid: the search origin
        :param entities: a collection of a certain type of entity, by Id type
        :param entity_search: the location of objects of this entity type, registered at a high-level grid resolution
        :param sim_h3_search_resolution: the h3 resolution of the entity_search collection
        :param is_valid: a function used to filter valid search results, such as checking stations for charger_id availability
        :param k: the number of concentric rings to check in the high-level search
        :param max_search_distance_km: the maximum distance a result can be from the search origin
        :return: the nearest entity, or, None if not found within the constraints
        """
        return cls.nearest_entity(
            geoid=geoid,
            entities=entities,
            entity_search=entity_search,
            sim_h3_search_resolution=sim_h3_search_resolution,
            is_valid=is_valid,
            distance_function=lambda e: cls.great_circle_distance(geoid, e.geoid),
            max_search_distance_km=max_search_distance_km,
        )

    @classmethod
    def nearest_entity(
        cls,
        geoid: GeoId,
        entities: Iterable[Entity],
        entity_search: immutables.Map[GeoId, FrozenSet[EntityId]],
        sim_h3_search_resolution: int,
        distance_function: Callable[[Any], float],
        is_valid: Callable[[Any], bool] = lambda x: True,
        max_search_distance_km: Kilometers = 10,  # kilometers
    ) -> Optional[Entity]:
        """
        returns the closest entity to the given geoid. In the case of a tie, the first entity encountered is returned.
        invariant: the Entity has a geoid field (Entity.geoid)


        :param geoid: the search origin
        :param entities: a collection of a certain type of entity, by Id type
        :param entity_search: the location of objects of this entity type, registered at a high-level grid resolution
        :param sim_h3_search_resolution: the h3 resolution of the entity_search collection
        :param is_valid: a function used to filter valid search results, such as checking stations for charger_id availability
        :param distance_function: a function used to evaluate the distance metric for selection
        :param k: the number of concentric rings to check in the high-level search
        :param max_search_distance_km: the maximum distance a result can be from the search origin
        :return: the nearest entity, or, None if not found within the constraints
        """
        if not entities:
            return None
        geoid_res = h3.h3_get_resolution(geoid)
        if geoid_res < sim_h3_search_resolution:
            raise H3Error("search resolution must be less than geoid resolution")

        k_dist_km = h3.edge_length(sim_h3_search_resolution, unit="km") * 2  # kilometers
        max_k = ceil(max_search_distance_km / k_dist_km)
        search_geoid = h3.h3_to_parent(geoid, sim_h3_search_resolution)

        def _search(current_k: int = 0) -> Optional[Entity]:
            if current_k > max_k:
                # There are no entities in any of the rings.
                return None
            else:
                # get the kth ring
                ring = h3.k_ring(search_geoid, current_k)

                # get all entities in this ring
                found = (
                    entity
                    for cell in ring
                    for entity in cls.get_entities_at_cell(cell, entity_search, entities)
                )

                best_dist_km = 1000000.0
                best_entity = None

                count = 0
                for entity in found:
                    dist_km = distance_function(entity)
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
    def get_entities_at_cell(
        cls,
        search_cell: GeoId,
        entity_search: immutables.Map[GeoId, FrozenSet[EntityId]],
        entities: Iterable[Entity],
    ) -> Tuple[Entity, ...]:
        """
        gives us entities within a high-level search cell


        :param search_cell: the search-level h3 position we are looking at
        :param entity_search: the upper-level search collection for this entity type
        :param entities: the actual entities
        :return: any entities which are located at this search-level cell
        """
        locations_at_cell = entity_search.get(search_cell)
        if locations_at_cell is None:
            return ()
        else:
            found = tuple(e for e in entities if e.id in locations_at_cell)
            return found

    @classmethod
    def nearest_entity_point_to_point(
        cls,
        geoid: GeoId,
        entities: Dict[EntityId, Entity],
        entity_locations: immutables.Map[GeoId, Tuple[EntityId, ...]],
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

        best_dist_km = 1000000.0
        best_e = None
        for e_geoid, e_ids in DictOps.iterate_items(entity_locations):
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
    def point_along_link(cls, link: LinkTraversal, available_time_seconds: Seconds) -> GeoId:
        """
        finds the GeoId which is some percentage between two GeoIds along a line


        :param available_time_seconds: the amount of time to traverse
        :param link: the link we are finding a mid point along
        :return: a GeoId along the Link
        """

        threshold = 0.000001
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
