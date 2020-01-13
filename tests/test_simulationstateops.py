from unittest import TestCase

from tests.mock_lobster import *


class TestSimulationStateOps(TestCase):
    def test_initial_simulation_state(self):
        """
        tests that the vehicles, stations, and bases provided appear
        in the simulation and can be found using expected geohashes
        invariant: none
        """
        # build sim state
        sim, failures = initial_simulation_state(
            mock_network(),
            (self.mock_veh_1, self.mock_veh_2),
            (self.mock_station_1, self.mock_station_2),
            (self.mock_base_1, self.mock_base_2),
        )

        # head check
        self.assertIsInstance(sim, SimulationState)
        self.assertEqual(len(failures), 0)

        # everything found at its id
        self.assertEqual(sim.vehicles[self.mock_veh_1.id], self.mock_veh_1)
        self.assertEqual(sim.vehicles[self.mock_veh_2.id], self.mock_veh_2)
        self.assertEqual(sim.stations[self.mock_station_1.id], self.mock_station_1)
        self.assertEqual(sim.stations[self.mock_station_2.id], self.mock_station_2)
        self.assertEqual(sim.bases[self.mock_base_1.id], self.mock_base_1)
        self.assertEqual(sim.bases[self.mock_base_2.id], self.mock_base_2)

        # vehicles were properly geo-coded (reverse lookup)
        self.assertIn(self.mock_veh_1.id, sim.v_locations[self.mock_veh_1.geoid])
        self.assertIn(self.mock_veh_2.id, sim.v_locations[self.mock_veh_2.geoid])

        # stations were properly geo-coded (reverse lookup)
        self.assertIn(self.mock_station_1.id, sim.s_locations[self.mock_station_1.geoid])
        self.assertIn(self.mock_station_2.id, sim.s_locations[self.mock_station_2.geoid])

        # bases were properly geo-coded (reverse lookup)
        self.assertIn(self.mock_base_1.id, sim.b_locations[self.mock_base_1.geoid])
        self.assertIn(self.mock_base_2.id, sim.b_locations[self.mock_base_2.geoid])

    def test_initial_simulation_state_bad_coordinates(self):
        """
        uses a road network that claims that all coordinates/positions
        are outside of the simulation/geofence. all errors should be
        returned.
        """
        # build sim state
        sim, failures = initial_simulation_state(
            self.MockRoadNetworkBadCoordinates(),
            (self.mock_veh_1, self.mock_veh_2),
            (self.mock_station_1, self.mock_station_2),
            (self.mock_base_1, self.mock_base_2)
        )

        number_of_things_added = 6

        # head check
        self.assertIsInstance(sim, SimulationState)
        self.assertEqual(len(failures), number_of_things_added)

    def test_initial_simulation_vehicles_at_same_location(self):
        """
        confirms that things at the same location are correctly
        represented in the state.
        invariant: the two mock vehicles should have the same coordinates
        """
        # build sim state
        sim, failures = initial_simulation_state(
            mock_network(),
            (self.mock_veh_1, self.mock_veh_2),
            (self.mock_station_1, self.mock_station_2),
            (self.mock_base_1, self.mock_base_2),
        )

        # head check
        self.assertIsInstance(sim, SimulationState)
        self.assertEqual(len(failures), 0)

        self.assertEqual(self.mock_veh_1.geoid, self.mock_veh_2.geoid, "both vehicles should be at the same location")
        vehicles_at_location = sim.v_locations[self.mock_veh_1.geoid]
        self.assertEqual(len(vehicles_at_location), 2)
        self.assertIn(self.mock_veh_1.id, vehicles_at_location)
        self.assertIn(self.mock_veh_2.id, vehicles_at_location)

    class MockRoadNetworkBadCoordinates(HaversineRoadNetwork):
        def geoid_within_geofence(self, geoid: GeoId) -> bool:
            return False

        def link_id_within_geofence(self, link_id: LinkId) -> bool:
            return False

        def geoid_within_simulation(self, geoid: GeoId) -> bool:
            return False

        def link_id_within_simulation(self, link_id: LinkId) -> bool:
            return False

    nearby = h3.geo_to_h3(0, 0.01, 15)
    mock_veh_1 = mock_vehicle_from_geoid(vehicle_id="m1")
    mock_veh_2 = mock_vehicle_from_geoid(vehicle_id="m2")
    mock_station_1 = mock_station_from_geoid(station_id="s1")
    mock_station_2 = mock_station_from_geoid(station_id="s2", geoid=nearby)

    mock_base_1 = mock_base(base_id="b1")
    mock_base_2 = mock_base(base_id="b2")
