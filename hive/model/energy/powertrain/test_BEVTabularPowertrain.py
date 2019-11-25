from unittest import TestCase
from typing import Union

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

    def test_leaf_energy_cost_real_route(self):
        powertrain = build_powertrain("leaf")
        cost = powertrain.energy_cost(_TestAssets.mock_route())
        cost


class _TestAssets:

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

    neighboring_hex_distance = H3Ops.distance_between_neighboring_hex_centroids(sim_h3_resolution)

    property_links = {
        # distance of 1.11 KM, speed of 10 KM/time unit, results in 0.1ish time units
        "1": PropertyLink.build(links["1"], 10, neighboring_hex_distance),
        "2": PropertyLink.build(links["2"], 10, neighboring_hex_distance),
        "3": PropertyLink.build(links["3"], 10, neighboring_hex_distance)
    }

    @classmethod
    def mock_route(cls):
        return cls.property_links["1"], cls.property_links["2"], cls.property_links["3"]
