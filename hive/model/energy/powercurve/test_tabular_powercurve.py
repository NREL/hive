from unittest import TestCase

from hive.model.energy.charger import Charger
from hive.model.energy.powercurve import build_powercurve, TabularPowercurve
from hive.model.energy.energysource import EnergySource
from hive.model.energy.energytype import EnergyType


class TestTabularPowercurve(TestCase):


    def test_leaf_build_energy_model(self):
        leaf_model = build_powercurve('leaf')
        self.assertIsInstance(leaf_model, TabularPowercurve)

    def test_leaf_energy_gain_0_soc(self):
        leaf_model = build_powercurve('leaf')
        energy_source = EnergySource("test_id", EnergyType.ELECTRIC, 50, 100, 0)
        one_hour = 3600.0
        result = leaf_model.refuel(energy_source, Charger.LEVEL_2, one_hour)
        self.assertAlmostEqual(result.load, 7.2, places=1)

    def test_leaf_energy_gain_full_soc(self):
        leaf_model = build_powercurve('leaf')
        energy_source = EnergySource("test_id", EnergyType.ELECTRIC, 50, 100, 50)
        self.assertTrue(energy_source.is_at_max_charge_acceptance(), "test precondition should be at max")
        one_hour = 3600.0
        result = leaf_model.refuel(energy_source, Charger.LEVEL_2, one_hour)
        self.assertAlmostEqual(result.soc, energy_source.soc)

    def test_leaf_energy_gain_50_percent_full(self):
        leaf_model = build_powercurve('leaf')
        energy_source = EnergySource("test_id", EnergyType.ELECTRIC, 50, 100, 25)
        one_hour = 3600.0
        result = leaf_model.refuel(energy_source, Charger.LEVEL_2, one_hour)
        self.assertAlmostEqual(result.load, 32, places=0)

    def test_leaf_energy_gain_interp_value(self):
        leaf_model = build_powercurve('leaf')
        energy_source = EnergySource("test_id", EnergyType.ELECTRIC, 50, 100, 48.91234)
        one_minute = 60.0
        result = leaf_model.refuel(energy_source, Charger.LEVEL_2, one_minute)
        self.assertAlmostEqual(result.load, 49, places=1)
