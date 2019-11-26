from unittest import TestCase

from hive.model.energy.energycurve import build_energycurve, TabularEnergyCurve
from hive.model.energy.energysource import EnergySource
from hive.model.energy.energytype import EnergyType


class TestTabularEnergyCurve(TestCase):
    def test_leaf_build_energy_model(self):
        leaf_model = build_energycurve('leaf')
        self.assertIsInstance(leaf_model, TabularEnergyCurve)

    def test_leaf_energy_gain_0_soc(self):
        leaf_model = build_energycurve('leaf')
        energy_source = EnergySource(EnergyType.ELECTRIC, 100, 0)
        result = leaf_model.energy_gain(energy_source)
        self.assertAlmostEqual(result, 10)

    def test_leaf_energy_gain_100_soc(self):
        leaf_model = build_energycurve('leaf')
        energy_source = EnergySource(EnergyType.ELECTRIC, 100, 100)
        result = leaf_model.energy_gain(energy_source)
        self.assertAlmostEqual(result, 0)

    def test_leaf_energy_gain_50_soc(self):
        leaf_model = build_energycurve('leaf')
        energy_source = EnergySource(EnergyType.ELECTRIC, 100, 50)
        result = leaf_model.energy_gain(energy_source)
        self.assertAlmostEqual(result, 45.61)

    def test_leaf_energy_gain_interp_value(self):
        leaf_model = build_energycurve('leaf')
        energy_source = EnergySource(EnergyType.ELECTRIC, 100, 48.91234)
        result = leaf_model.energy_gain(energy_source)
        self.assertAlmostEqual(result, 45)