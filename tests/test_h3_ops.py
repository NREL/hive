from unittest import TestCase

import h3
import immutables
from nrel.hive.model.roadnetwork.link import Link
from nrel.hive.resources.mock_lobster import mock_request_from_geoids, mock_sim
from nrel.hive.state.simulation_state import simulation_state_ops

from nrel.hive.util.h3_ops import H3Ops
from nrel.hive.util.fp import throw_or_return
from nrel.hive.util.units import hours_to_seconds


class TestH3Ops(TestCase):
    def test_point_along_link(self):
        # endpoints are about 1km apart
        start = h3.geo_to_h3(37, 122, 15)
        end = h3.geo_to_h3(37.008994, 122, 15)

        # create links with 1km speed
        fwd_link = Link.build("test", start, end, speed_kmph=1)
        bwd_link = Link.build("test", end, start, speed_kmph=1)

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
        entities = immutables.Map({"1": 1, "2": 2, "3": 3, "4": 4})
        entity_locations = immutables.Map(
            {close_to_somewhere: ("1", "2"), far_from_somewhere: ("3", "4")}
        )

        nearest_entity = H3Ops.nearest_entity_point_to_point(somewhere, entities, entity_locations)

        self.assertEqual(nearest_entity, 1, "should have returned 1")

    def test_nearest_entity(self):
        """
        this is easiest to test by creating a Sim State with an entity in it
        """

        h3_resolution = 15
        h3_search_res = 7
        somewhere = h3.geo_to_h3(39.7539, -104.974, h3_resolution)
        near_to_somewhere = h3.geo_to_h3(39.754, -104.975, h3_resolution)
        far_from_somewhere = h3.geo_to_h3(39.755, -104.976, h3_resolution)
        req_near = mock_request_from_geoids(origin=somewhere, destination=near_to_somewhere)
        req_far = mock_request_from_geoids(origin=somewhere, destination=far_from_somewhere)

        sim = mock_sim(h3_location_res=h3_resolution, h3_search_res=h3_search_res)
        sim_with_req1 = throw_or_return(simulation_state_ops.add_request_safe(sim, req_near))
        sim_with_reqs = throw_or_return(
            simulation_state_ops.add_request_safe(sim_with_req1, req_far)
        )

        nearest = H3Ops.nearest_entity_by_great_circle_distance(
            geoid=somewhere,
            entities=tuple(sim_with_reqs.get_requests()),
            entity_search=sim_with_reqs.r_search,
            sim_h3_search_resolution=sim_with_reqs.sim_h3_search_resolution,
        )

        self.assertEqual(nearest.geoid, req_near.geoid)

    def test_great_circle_distance(self):
        london = h3.geo_to_h3(51.5007, 0.1246, 10)
        new_york = h3.geo_to_h3(40.6892, 74.0445, 10)

        distance_km = H3Ops.great_circle_distance(london, new_york)

        self.assertAlmostEqual(distance_km, 5574.8, places=1)
