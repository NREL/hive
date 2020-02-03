from unittest import TestCase

import immutables
from h3 import h3

from hive.model.request import Request
from hive.model.roadnetwork.link import Link
from hive.model.roadnetwork.property_link import PropertyLink
from hive.util.helpers import H3Ops
from hive.util.units import hours_to_seconds
from tests.mock_lobster import mock_sim


class TestH3Ops(TestCase):
    def test_point_along_link(self):
        # endpoints are about 1km apart
        start = h3.geo_to_h3(37, 122, 15)
        end = h3.geo_to_h3(37.008994, 122, 15)

        # create links with 1km speed
        fwd_link = PropertyLink.build(Link("test", start, end), 1)
        bwd_link = PropertyLink.build(Link("test", end, start), 1)

        # test moving forward and backward, each by a half-unit of time
        fwd_result = H3Ops.point_along_link(fwd_link, hours_to_seconds(0.5))
        bwd_result = H3Ops.point_along_link(bwd_link, hours_to_seconds(0.5))

        # check that the point is half-way
        fwd_lat, fwd_lon = h3.h3_to_geo(fwd_result)
        self.assertAlmostEqual(fwd_lat, 37.004, places=2)
        self.assertAlmostEqual(fwd_lon, 122, places=2)

        bwd_lat, bwd_lon = h3.h3_to_geo(bwd_result)
        self.assertAlmostEqual(bwd_lat, 37.004, places=2)
        self.assertAlmostEqual(bwd_lon, 122, places=2)

    def test_nearest_entity_point_to_point(self):
        somewhere = h3.geo_to_h3(39.748971, -104.992323, 15)
        close_to_somewhere = h3.geo_to_h3(39.753600, -104.993369, 15)
        far_from_somewhere = h3.geo_to_h3(39.728882, -105.002792, 15)
        entities = immutables.Map({'1': 1, '2': 2, '3': 3, '4': 4})
        entity_locations = immutables.Map({close_to_somewhere: ('1', '2'), far_from_somewhere: ('3', '4')})

        nearest_entity = H3Ops.nearest_entity_point_to_point(somewhere, entities, entity_locations)

        self.assertEqual(nearest_entity, 1, "should have returned 1")

    def test_nearest_entity(self):
        """
        this is easiest to test by creating a Sim State with an entity in it
        """

        h3_resolution = 15
        h3_search_res = 7
        somewhere = h3.geo_to_h3(39.748971, -104.992323, h3_resolution)
        near_to_somewhere = h3.geo_to_h3(39.753600, -104.993369, h3_resolution)
        far_from_somewhere = h3.geo_to_h3(39.728882, -105.002792, h3_resolution)
        req_near = Request("req_near", near_to_somewhere, somewhere, 0, 0, ())
        req_far = Request("req_far", far_from_somewhere, somewhere, 0, 0, ())

        sim = mock_sim(h3_location_res=h3_resolution, h3_search_res=h3_search_res)
        sim_with_reqs = sim.add_request(req_near).add_request(req_far)

        nearest = H3Ops.nearest_entity(geoid=somewhere,
                                       entities=sim_with_reqs.requests,
                                       entity_search=sim_with_reqs.r_search,
                                       sim_h3_search_resolution=sim_with_reqs.sim_h3_search_resolution)

        self.assertEqual(nearest.geoid, req_near.geoid)
