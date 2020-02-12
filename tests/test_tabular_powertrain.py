from unittest import TestCase

from hive.model.energy.powertrain import build_powertrain
from hive.model.energy.powertrain.tabular_powertrain import TabularPowertrain
from tests.mock_lobster import *


class TestTabularPowertrain(TestCase):
    def test_leaf_build_powertrain(self):
        leaf_model = build_powertrain("leaf")
        self.assertIsInstance(leaf_model, TabularPowertrain)

    def test_leaf_energy_cost_empty_route(self):
        powertrain = build_powertrain("leaf")
        cost_kwh = powertrain.energy_cost(())
        self.assertEqual(cost_kwh, 0.0, "empty route should yield zero energy cost")

    def test_leaf_energy_cost_real_route(self):
        """
        the distance should be 3km;
        the speed being 45kmph results in a lookup watthours per km of ~102.5
        so, the result should be around .308 kilowatthour.
        :return:
        """
        powertrain = build_powertrain("leaf")
        test_route = mock_route(speed_kmph=45)
        cost_kwh = powertrain.energy_cost(test_route)
        self.assertAlmostEqual(cost_kwh, .308, places=1)