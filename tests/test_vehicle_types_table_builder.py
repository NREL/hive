from unittest import TestCase

from pkg_resources import resource_filename

from hive.model.vehicle.vehicle_type import VehicleTypesTableBuilder


class TestVehicleTypesTableBuilder(TestCase):
    def test_build(self):
        file = resource_filename("hive.resources.vehicle_types", "default_vehicle_types.csv")

        builder = VehicleTypesTableBuilder.build(file)
        self.assertEqual(len(builder.errors), 0, f"builder should have no errors with known file {file}")
        self.assertIn("leaf_50", builder.result, "should have loaded the default vehicle type")

    def test_build_bad_key(self):
        input_with_bad_value = iter([
            {
                "vehicle_type_id": "leaf_50",
                "powertrain_id": "leaf",
                "powercurve_id": "leaf",
                "pumpkin_latte_special": "50",
                "max_charge_acceptance_kw": "50",
                "operating_cost_km": "0.1"
            }
        ])
        builder = VehicleTypesTableBuilder.build(input_with_bad_value)
        self.assertIsNotNone(builder.errors, f"builder should have a KeyError from capacity")
        self.assertIsInstance(builder.errors[0], KeyError)

    def test_build_bad_value(self):
        input_with_bad_value = iter([
            {
                "vehicle_type_id": "leaf_50",
                "powertrain_id": "leaf",
                "powercurve_id": "leaf",
                "capacity_kwh": "not-a-number",
                "max_charge_acceptance_kw": "50",
                "operating_cost_km": "0.1"
            }
        ])
        builder = VehicleTypesTableBuilder.build(input_with_bad_value)
        self.assertIsNotNone(builder.errors, f"builder should have a ValueError from capacity")
        self.assertIsInstance(builder.errors[0], ValueError)

    def test_build_bad_key_and_value(self):
        input_with_bad_value = iter([
            {
                "vehicle_type_id": "leaf_50",
                "powertrain_id": "leaf",
                "powercurve_id": "leaf",
                "pumpkin_latte_special": "50",
                "max_charge_acceptance_kw": "maple pancakes with a pastry stout",
                "operating_cost_km": "0.1"
            }
        ])
        builder = VehicleTypesTableBuilder.build(input_with_bad_value)
        self.assertIsNotNone(builder.errors, "builder should have errors")
        self.assertIs(len(builder.errors), 2, "builder should have exactly two errors")
        self.assertIsInstance(builder.errors[0], KeyError)
        self.assertIsInstance(builder.errors[1], ValueError)
