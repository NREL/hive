from __future__ import annotations

from typing import NamedTuple, Dict

from h3 import h3

import json

from hive.util.typealiases import GeoFenceSet, H3Resolution, GeoId
from hive.util.exception import H3Error


class GeoFence(NamedTuple):
    geofence_set: GeoFenceSet
    h3_resolution: H3Resolution

    @classmethod
    def from_geojson_file(cls, geosjon_file: str, h3_resolution: H3Resolution = 10) -> GeoFence:
        with open(geosjon_file, 'r') as gj:
            geojson = json.loads(gj.read())

        return GeoFence.from_geojson(geojson, h3_resolution)

    @classmethod
    def from_geojson(cls, geojson: Dict, h3_resolution: H3Resolution = 10) -> GeoFence:
        geofence_set = frozenset(h3.polyfill(
            geo_json=geojson['features'][0]['geometry'] if 'features' in geojson else geojson['geometry'],
            res=h3_resolution,
            geo_json_conformant=True))

        return GeoFence(
            geofence_set=geofence_set,
            h3_resolution=h3_resolution,
        )

    def contains(self, geoid: GeoId) -> bool:
        geoid_res = h3.h3_get_resolution(geoid)
        if geoid_res < self.h3_resolution:
            raise H3Error('geofence resolution must be less than geoid resolution')

        parent_geoid = h3.h3_to_parent(geoid, self.h3_resolution)
        return parent_geoid in self.geofence_set
