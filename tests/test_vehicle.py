from csv import DictReader
from unittest import TestCase

from tests.mock_lobster import *


class TestVehicle(TestCase):
    def test_modify_energy_source(self):
        veh = mock_vehicle()
        new_soc = 0.99
        batt = mock_energy_source(soc=new_soc)
        updated_vehicle = veh.modify_energy_source(batt)

        self.assertEqual(updated_vehicle.energy_source.soc, new_soc, "should have the new battery's soc")

    def test_from_row(self):
        source = """vehicle_id,lat,lon,vehicle_type_id,initial_soc
                    v1,39.7539,-104.976,vt0,1.0"""

        row = next(DictReader(source.split()))
        road_network = mock_network()
        env = mock_env()
        expected_geoid = h3.geo_to_h3(39.7539, -104.976, road_network.sim_h3_resolution)

        vehicle = Vehicle.from_row(row, road_network, env)

        self.assertEqual(vehicle.id, "v1")
        self.assertEqual(vehicle.geoid, expected_geoid)
        self.assertEqual(vehicle.powercurve_id, 'pc0')
        self.assertEqual(vehicle.powertrain_id, 'pt0')
        self.assertEqual(vehicle.energy_source.powercurve_id, 'pc0')
        self.assertEqual(vehicle.energy_source.energy_kwh, 100.0)
        self.assertEqual(vehicle.energy_source.capacity_kwh, 100.0)
        self.assertEqual(vehicle.energy_source.energy_type, EnergyType.ELECTRIC)
        self.assertEqual(vehicle.energy_source.max_charge_acceptance_kw, 50.0)
        self.assertEqual(vehicle.link.start, expected_geoid)
        self.assertIsInstance(vehicle.vehicle_state, Idle)
        self.assertEqual(vehicle.distance_traveled_km, 0)
        self.assertEqual(vehicle.idle_time_seconds, 0)

    def test_from_row_bad_vehicle_type_id(self):
        source = """vehicle_id,lat,lon,vehicle_type_id,initial_soc
                    v1,39.7539,-104.976,beef!@#$,1.0"""

        row = next(DictReader(source.split()))
        road_network = mock_network()
        env = mock_env()

        with self.assertRaises(IOError):
            Vehicle.from_row(row, road_network, env)
