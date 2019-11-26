from unittest import TestCase

from h3 import h3

from hive.model.roadnetwork.link import Link
from hive.model.roadnetwork.property_link import PropertyLink
from hive.util.helpers import H3Ops


class TestH3Ops(TestCase):
    def test_point_along_link(self):
        start = h3.geo_to_h3(37, 122, 15)
        end = h3.geo_to_h3(37.008994, 122, 15) # 1km
        property_link = PropertyLink.build(Link("test", start, end), 1) #1km per unit time
        result = H3Ops.point_along_link(property_link, 0.5) # half a unit time
        # todo: need an equation which moves in the correct direction regardless of start/end values
        #  being positive/negative (i'm sure it exists)
        result
