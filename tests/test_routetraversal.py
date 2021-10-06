from unittest import TestCase

from hive.model.roadnetwork.linktraversal import traverse_up_to
from hive.model.roadnetwork.routetraversal import traverse
from hive.resources.mock_lobster import *


class TestRouteTraversal(TestCase):
    def test_traverse_with_enough_time(self):
        """
        the mock problem is tuned to complete the route with a time step of just beyond 3 time units
        """
        links = mock_route()

        _, result = traverse(
            route_estimate=links,
            duration_seconds=hours_to_seconds(4)
        )
        self.assertGreater(result.remaining_time_seconds, 0, "should have more time left")
        self.assertEqual(len(result.remaining_route), 0, "should have no more route")
        self.assertEqual(len(result.experienced_route), 3, "should have hit all 3 links")

    def test_traverse_without_enough_time(self):
        """
        the mock problem needs more than 1.5 time to complete the route. should end
        up somewhere in the middle
        """
        links = mock_route()
        _, result = traverse(
            route_estimate=links,
            duration_seconds=hours_to_seconds(1.5)  # 1.5 hours at 1kmph, 1km per link, 3 links
        )
        self.assertEqual(result.remaining_time_seconds, 0, "should have no more time left")
        self.assertEqual(len(result.remaining_route), 2, "should have 2 links remaining")
        self.assertEqual(len(result.experienced_route), 2, "should have traversed 2 links")

    def test_traverse_up_to_split(self):
        links = mock_route()
        test_link = links[0]

        error, result = traverse_up_to(
            link=test_link,
            available_time_seconds=hours_to_seconds(0.5),
        )

        traversed = result.traversed
        remaining = result.remaining

        self.assertEqual(test_link.start, traversed.start, "Original link and traversed link should share start")
        self.assertEqual(test_link.end, remaining.end, "Original link and remaining link should share end")
        self.assertEqual(traversed.end, remaining.start, "Traversed end should match remaining start")

    def test_traverse_up_to_no_split(self):
        links = mock_route()
        test_link = links[0]

        error, result = traverse_up_to(
            link=test_link,
            available_time_seconds=hours_to_seconds(4),
        )

        traversed = result.traversed
        remaining = result.remaining

        self.assertEqual(test_link.start, traversed.start, "Original link and traversed link should share start")
        self.assertEqual(test_link.end, traversed.end, "Original link and traversed link should share end")
        self.assertIsNone(remaining, "There should be no remaining route")
