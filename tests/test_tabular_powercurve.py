from unittest import TestCase

from hive.model.energy.charger import Charger
from hive.model.energy.powercurve import build_powercurve, TabularPowercurve
from hive.model.energy.energysource import EnergySource
from hive.model.energy.energytype import EnergyType
from hive.util.units import unit


class TestTabularPowercurve(TestCase):

    def test_leaf_build_energy_model(self):
        leaf_model = build_powercurve('leaf')
        self.assertIsInstance(leaf_model, TabularPowercurve)

    def test_leaf_energy_gain_0_soc(self):
        leaf_model = build_powercurve('leaf')
        energy_source = EnergySource("test_id",
                                     energy_type=EnergyType.ELECTRIC,
                                     capacity=50*unit.kilowatthour,
                                     energy=0*unit.kilowatthour,
                                     ideal_energy_limit=40*unit.kilowatthour,
                                     max_charge_acceptance_kw=50*unit.kilowatt,
                                     )

        result = leaf_model.refuel(energy_source, Charger.DCFC, 2 * 3600.0)
        self.assertEqual(result.is_at_ideal_energy_limit(), True, "Should have fully charged")

    def test_leaf_energy_gain_full_soc(self):
        leaf_model = build_powercurve('leaf')
        energy_source = EnergySource("test_id",
                                     energy_type=EnergyType.ELECTRIC,
                                     capacity=50*unit.kilowatthour,
                                     energy=50*unit.kilowatthour,
                                     ideal_energy_limit=50*unit.kilowatthour,
                                     max_charge_acceptance_kw=50*unit.kilowatt,
                                     )
        self.assertTrue(energy_source.is_at_ideal_energy_limit(), "test precondition should be at max")
        result = leaf_model.refuel(energy_source, Charger.DCFC, 1)
        self.assertAlmostEqual(result.soc, energy_source.soc)

    def test_leaf_energy_gain_low_power(self):
        leaf_model = build_powercurve('leaf')
        energy_source = EnergySource("test_id",
                                     energy_type=EnergyType.ELECTRIC,
                                     capacity=50*unit.kilowatthour,
                                     energy=0*unit.kilowatthour,
                                     ideal_energy_limit=50*unit.kilowatthour,
                                     max_charge_acceptance_kw=50*unit.kilowatt,
                                     )
        result = leaf_model.refuel(energy_source, Charger.LEVEL_2, 1 * 3600)
        self.assertEqual(result.not_at_ideal_energy_limit(), True, "Should not have had enough time to charge to full")

