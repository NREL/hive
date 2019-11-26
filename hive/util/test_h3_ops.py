from unittest import TestCase

from h3 import h3

from hive.model.roadnetwork.link import Link
from hive.model.roadnetwork.property_link import PropertyLink
from hive.util.helpers import H3Ops


class TestH3Ops(TestCase):
    def test_point_along_link(self):
        # endpoints are about 1km apart
        start = h3.geo_to_h3(37, 122, 15)
        end = h3.geo_to_h3(37.008994, 122, 15)

        # create links with 1km speed
        fwd_link = PropertyLink.build(Link("test", start, end), 1)
        bwd_link = PropertyLink.build(Link("test", end, start), 1)

        # test moving forward and backward, each by a half-unit of time
        fwd_result = H3Ops.point_along_link(fwd_link, 0.5)
        bwd_result = H3Ops.point_along_link(bwd_link, 0.5)

        # check that the point is half-way
        fwd_lat, fwd_lon = h3.h3_to_geo(fwd_result)
        self.assertAlmostEqual(fwd_lat, 37.004, places=2)
        self.assertAlmostEqual(fwd_lon, 122, places=2)

        bwd_lat, bwd_lon = h3.h3_to_geo(bwd_result)
        self.assertAlmostEqual(bwd_lat, 37.004, places=2)
        self.assertAlmostEqual(bwd_lon, 122, places=2)
