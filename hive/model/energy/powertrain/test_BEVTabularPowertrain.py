from unittest import TestCase, skip

from h3 import h3

from hive.model.energy.powertrain import build_powertrain
from hive.model.energy.powertrain.bev_tabular_powertrain import BEVTabularPowertrain
from hive.model.roadnetwork.link import Link
from hive.model.roadnetwork.property_link import PropertyLink
from hive.util.helpers import H3Ops


class TestBEVTabularPowertrain(TestCase):
    def test_leaf_build_powertrain(self):
        leaf_model = build_powertrain("leaf")
        self.assertIsInstance(leaf_model, BEVTabularPowertrain)

    def test_leaf_energy_cost_empty_route(self):
        powertrain = build_powertrain("leaf")
        cost = powertrain.energy_cost(())
        self.assertEqual(cost, 0.0, "empty route should yield zero energy cost")

    @skip
    def test_leaf_energy_cost_real_route(self):
        """
        the distance should be 3km;
        the speed being 45kmph results in a lookup watts per km of ~0.57
        so, the result should be around 1.71.
        :return:
        """
        powertrain = build_powertrain("leaf")
        test_route = _TestAssets.mock_route()
        cost = powertrain.energy_cost(test_route)
        self.assertAlmostEqual(cost, 1.71, places=2)


class _TestAssets:

    sim_h3_resolution = 15

    # each link is approx. 1000.09 meters long (1km)
    links = {
        "1": Link("1",
                  h3.geo_to_h3(37, 122, sim_h3_resolution),
                  h3.geo_to_h3(37.008994, 122, sim_h3_resolution)),
        "2": Link("2",
                  h3.geo_to_h3(37.008994, 122, sim_h3_resolution),
                  h3.geo_to_h3(37.017998, 122, sim_h3_resolution)),
        "3": Link("3",
                  h3.geo_to_h3(37.017998, 122, sim_h3_resolution),
                  h3.geo_to_h3(37.026992, 122, sim_h3_resolution)),
    }

    neighboring_hex_distance = H3Ops.distance_between_neighboring_hex_centroids(sim_h3_resolution)

    property_links = {
        # 45kmph with leaf model should be about .57 watts per km, or about 1.5watts for this trip
        "1": PropertyLink.build(links["1"], 45, neighboring_hex_distance),
        "2": PropertyLink.build(links["2"], 45, neighboring_hex_distance),
        "3": PropertyLink.build(links["3"], 45, neighboring_hex_distance)
    }

    @classmethod
    def mock_route(cls):
        return cls.property_links["1"], cls.property_links["2"], cls.property_links["3"]
