from typing import Tuple, Optional
from unittest import TestCase

from hive.roadnetwork.link import PropertyLink, Link
from hive.roadnetwork.roadnetwork import RoadNetwork
from hive.roadnetwork.routetraversal import traverse
from hive.util.typealiases import LinkId, GeoId

from h3 import h3


class TestRouteTraversal(TestCase):
    def test_should_end_traversal(self):
        self.fail()

    def test_add_traversal(self):
        self.fail()

    def test_add_link_not_traversed(self):
        self.fail()

    def test_traverse_with_enough_time(self):
        """
        the mock problem is tuned to complete the route with a time step of 1
        """
        network = TestRouteTraversalAssets.mock_network()
        links = TestRouteTraversalAssets.mock_links()
        result = traverse(
            route_estimate=links,
            road_network=network,
            time_step=1
        )
        self.assertGreater(result.remaining_time, 0, "should have more time left")
        self.assertEqual(len(result.remaining_route), 0, "should have no more route")
        self.assertEqual(len(result.experienced_route), 3, "should have hit all 3 links")

    def test_traverse_without_enough_time(self):
        """
        the mock problem needs more than 0.2 time to complete the route
        the amount that is completed is dependent on h3's transform from geo positioning
        of the centroids to lat/lon distances
        """
        network = TestRouteTraversalAssets.mock_network()
        links = TestRouteTraversalAssets.mock_links()
        result = traverse(
            route_estimate=links,
            road_network=network,
            time_step=0.2
        )
        self.assertEqual(result.remaining_time, 0, "should have no more time left")
        self.assertEqual(len(result.remaining_route), 2, "should have 2 links remaining")
        self.assertEqual(len(result.experienced_route), 2, "should have traversed 2 links")
        # todo: test that the "slice" of the middle link was done correctly?


class MockRoadNetwork(RoadNetwork):
    """
    a road network that only implements "get_link"
    """

    def __init__(self, property_links):
        self.sim_h3_resolution = 15
        self.property_links = property_links

    def route_by_geoid(self, origin: GeoId, destination: GeoId) -> Tuple[Link, ...]:
        pass

    def update(self, sim_time: int) -> RoadNetwork:
        pass

    def get_link(self, link_id: LinkId) -> Optional[PropertyLink]:
        if link_id in self.property_links:
            return self.property_links[link_id]
        else:
            return None


class TestRouteTraversalAssets:
    """
    a mock scenario with 3 road network links. their travel time each is in
    generic units.
    """

    sim_h3_resolution = 15

    links = {
        "1": Link("1",
                  h3.geo_to_h3(37, 122, sim_h3_resolution),
                  h3.geo_to_h3(37.01, 122, sim_h3_resolution)),
        "2": Link("2",
                  h3.geo_to_h3(37.01, 122, sim_h3_resolution),
                  h3.geo_to_h3(37.02, 122, sim_h3_resolution)),
        "3": Link("3",
                  h3.geo_to_h3(37.02, 122, sim_h3_resolution),
                  h3.geo_to_h3(37.03, 122, sim_h3_resolution)),
    }
    property_links = {
        # distance of 1.11 KM, speed of 10 KM/time unit, results in 0.1ish time units
        "1": PropertyLink("1", links["1"], 5.56, 10, 0.5),
        "2": PropertyLink("2", links["2"], 5.56, 10, 0.5),
        "3": PropertyLink("3", links["3"], 5.56, 10, 0.5)
    }

    @classmethod
    def mock_network(cls) -> RoadNetwork:
        return MockRoadNetwork(cls.property_links)

    @classmethod
    def mock_links(cls) -> Tuple[Link, ...]:
        return cls.links["1"], cls.links["2"], cls.links["3"]
