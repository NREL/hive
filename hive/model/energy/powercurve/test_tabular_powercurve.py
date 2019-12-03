from unittest import TestCase

from hive.model.energy.charger import Charger
from hive.model.energy.powercurve import build_energycurve, TabularPowerCurve
from hive.model.energy.energysource import EnergySource
from hive.model.energy.energytype import EnergyType


class TestTabularPowercurve(TestCase):
    def test_leaf_build_energy_model(self):
        leaf_model = build_energycurve('leaf')
        self.assertIsInstance(leaf_model, TabularPowerCurve)

    def test_leaf_energy_gain_0_soc(self):
        leaf_model = build_energycurve('leaf')
        energy_source = EnergySource("test_id", EnergyType.ELECTRIC, 100, 0)
        result = leaf_model.refuel(energy_source, Charger.LEVEL_2, 3600, 3600)
        self.assertAlmostEqual(result.load, 10)

    def test_leaf_energy_gain_100_soc(self):
        leaf_model = build_energycurve('leaf')
        energy_source = EnergySource("test_id", EnergyType.ELECTRIC, 100, 100)
        result = leaf_model.refuel(energy_source, Charger.LEVEL_2)
        self.assertAlmostEqual(result, 0)

    def test_leaf_energy_gain_50_soc(self):
        leaf_model = build_energycurve('leaf')
        energy_source = EnergySource("test_id", EnergyType.ELECTRIC, 100, 50)
        result = leaf_model.refuel(energy_source, Charger.LEVEL_2)
        self.assertAlmostEqual(result, 45.61)

    def test_leaf_energy_gain_interp_value(self):
        leaf_model = build_energycurve('leaf')
        energy_source = EnergySource("test_id", EnergyType.ELECTRIC, 100, 48.91234)
        result = leaf_model.refuel(energy_source, Charger.LEVEL_2)
        self.assertAlmostEqual(result, 45.5, places=0)
