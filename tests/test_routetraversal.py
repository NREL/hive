from unittest import TestCase

from nrel.hive.model.roadnetwork.linktraversal import traverse_up_to
from nrel.hive.model.roadnetwork.routetraversal import traverse
from nrel.hive.resources.mock_lobster import mock_osm_network, mock_osm_route, mock_route
from nrel.hive.util.units import hours_to_seconds


class TestRouteTraversal(TestCase):
    def test_traverse_with_enough_time(self):
        """
        the mock problem is tuned to complete the route with a time step of just beyond 3 time units
        """
        rn = mock_osm_network()
        route = mock_osm_route()

        _, result = traverse(
            route_estimate=route, duration_seconds=hours_to_seconds(4), road_network=rn
        )
        self.assertGreater(result.remaining_time_seconds, 0, "should have more time left")
        self.assertEqual(len(result.remaining_route), 0, "should have no more route")
        self.assertEqual(len(result.experienced_route), len(route), "should have hit all links")

    def test_traverse_without_enough_time(self):
        """
        should end up somewhere in the middle
        """
        rn = mock_osm_network()
        route = mock_osm_route()
        midway = int(len(route) / 2)
        midway_travel_time_seconds = sum([link.travel_time_seconds for link in route[:midway]])

        _, result = traverse(
            route_estimate=route,
            duration_seconds=midway_travel_time_seconds,
            road_network=rn,
        )
        self.assertEqual(result.remaining_time_seconds, 0, "should have no more time left")
        self.assertEqual(
            len(result.remaining_route), len(route[midway:]), "should have some route left"
        )
        self.assertEqual(len(result.experienced_route), midway, "should have hit half the links")

    def test_traverse_up_to_split(self):
        links = mock_route()
        test_link = links[0]

        error, result = traverse_up_to(
            link=test_link,
            available_time_seconds=hours_to_seconds(0.5),
        )

        traversed = result.traversed
        remaining = result.remaining

        self.assertEqual(
            test_link.start,
            traversed.start,
            "Original link and traversed link should share start",
        )
        self.assertEqual(
            test_link.end,
            remaining.end,
            "Original link and remaining link should share end",
        )
        self.assertEqual(
            traversed.end,
            remaining.start,
            "Traversed end should match remaining start",
        )

    def test_traverse_up_to_no_split(self):
        links = mock_route()
        test_link = links[0]

        error, result = traverse_up_to(
            link=test_link,
            available_time_seconds=hours_to_seconds(4),
        )

        traversed = result.traversed
        remaining = result.remaining

        self.assertEqual(
            test_link.start,
            traversed.start,
            "Original link and traversed link should share start",
        )
        self.assertEqual(
            test_link.end,
            traversed.end,
            "Original link and traversed link should share end",
        )
        self.assertIsNone(remaining, "There should be no remaining route")
