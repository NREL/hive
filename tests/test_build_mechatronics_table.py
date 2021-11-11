from unittest import TestCase
from pathlib import Path

from hive.model.vehicle.mechatronics.__init__ import build_mechatronics_table

test_dir = Path(__file__).parent



class TestBuildMechatronicsTable(TestCase):

    def test_build_valid_table(self):
        try:
            build_mechatronics_table(test_dir / 'test_assets/mechatronics_valid.yaml',
                                     'hive.resources.scenarios.denver_downtown')
        except KeyError:
            self.fail("build_mechatronics_table threw KeyError unexpectedly!")

    def test_missing_type_field(self):
        self.assertRaises(IOError,
                          build_mechatronics_table,
                          test_dir / 'test_assets/mechatronics_missing_type.yaml',
                          'hive.resources.scenarios.denver_downtown')

    def test_bad_type(self):
        self.assertRaises(IOError,
                          build_mechatronics_table,
                          test_dir / 'test_assets/mechatronics_bad_type.yaml',
                          'hive.resources.scenarios.denver_downtown')

    def test_missing_power_curve_field(self):
        self.assertRaises(FileNotFoundError,
                          build_mechatronics_table,
                          test_dir / 'test_assets/mechatronics_missing_powercurve.yaml',
                          'hive.resources.scenarios.denver_downtown')

    def test_bad_power_curve(self):
        self.assertRaises(FileNotFoundError,
                          build_mechatronics_table,
                          test_dir / 'test_assets/mechatronics_bad_powercurve.yaml',
                          'hive.resources.scenarios.denver_downtown')

    def test_missing_power_train_field(self):
        self.assertRaises(FileNotFoundError,
                          build_mechatronics_table,
                          test_dir / 'test_assets/mechatronics_missing_powertrain.yaml',
                          'hive.resources.scenarios.denver_downtown')

    def test_bad_power_train_name(self):
        self.assertRaises(FileNotFoundError,
                          build_mechatronics_table,
                          test_dir / 'test_assets/mechatronics_bad_powertrain.yaml',
                          'hive.resources.scenarios.denver_downtown')

    def test_missing_mechatronics_file(self):
        self.assertRaises(FileNotFoundError,
                          build_mechatronics_table,
                          test_dir / 'test_assets/not_real_mechatronics.yaml',
                          'hive.resources.scenarios.denver_downtown')
