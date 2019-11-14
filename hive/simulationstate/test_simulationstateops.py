from unittest import TestCase

from h3 import h3

from hive.model.base import Base
from hive.model.battery import Battery
from hive.model.coordinate import Coordinate
from hive.model.engine import Engine
from hive.model.station import Station
from hive.model.vehicle import Vehicle
from hive.roadnetwork.position import Position
from hive.roadnetwork.roadnetwork import RoadNetwork
from hive.roadnetwork.route import Route
from hive.roadnetwork.routestep import RouteStep
from hive.simulationstate.simulationstate import SimulationState
from hive.simulationstate.simulationstateops import initial_simulation_state
from hive.util.typealiases import *


class TestSimulationStateOps(TestCase):
    def test_initial_simulation_state(self):
        """
        tests that the vehicles, stations, and bases provided appear
        in the simulation and can be found using expected geohashes
        invariant: none
        """
        # build sim state
        sim, failures = initial_simulation_state(
            self.MockRoadNetwork(),
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
        m1_coord = sim.road_network.position_to_geoid(self.mock_veh_1.position)
        m2_coord = sim.road_network.position_to_geoid(self.mock_veh_2.position)
        m1_geoid = h3.geo_to_h3(m1_coord.lat, m1_coord.lon, sim.sim_h3_resolution)
        m2_geoid = h3.geo_to_h3(m2_coord.lat, m2_coord.lon, sim.sim_h3_resolution)
        self.assertIn(self.mock_veh_1.id, sim.v_locations[m1_geoid])
        self.assertIn(self.mock_veh_2.id, sim.v_locations[m2_geoid])

        # stations were properly geo-coded (reverse lookup)
        s1_geoid = h3.geo_to_h3(self.mock_station_1.coordinate.lat,
                                self.mock_station_1.coordinate.lon,
                                sim.sim_h3_resolution)
        s2_geoid = h3.geo_to_h3(self.mock_station_2.coordinate.lat,
                                self.mock_station_2.coordinate.lon,
                                sim.sim_h3_resolution)
        self.assertIn(self.mock_station_1.id, sim.s_locations[s1_geoid])
        self.assertIn(self.mock_station_2.id, sim.s_locations[s2_geoid])

        # bases were properly geo-coded (reverse lookup)
        b1_geoid = h3.geo_to_h3(self.mock_base_1.coordinate.lat,
                                self.mock_base_1.coordinate.lon,
                                sim.sim_h3_resolution)
        b2_geoid = h3.geo_to_h3(self.mock_base_2.coordinate.lat,
                                self.mock_base_2.coordinate.lon,
                                sim.sim_h3_resolution)
        self.assertIn(self.mock_base_1.id, sim.b_locations[b1_geoid])
        self.assertIn(self.mock_base_2.id, sim.b_locations[b2_geoid])

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
            self.MockRoadNetwork(),
            (self.mock_veh_1, self.mock_veh_2),
            (self.mock_station_1, self.mock_station_2),
            (self.mock_base_1, self.mock_base_2),
        )

        # head check
        self.assertIsInstance(sim, SimulationState)
        self.assertEqual(len(failures), 0)

        m1_coord = sim.road_network.position_to_geoid(self.mock_veh_1.position)
        m2_coord = sim.road_network.position_to_geoid(self.mock_veh_2.position)
        m1_geoid = h3.geo_to_h3(m1_coord.lat, m1_coord.lon, sim.sim_h3_resolution)
        m2_geoid = h3.geo_to_h3(m2_coord.lat, m2_coord.lon, sim.sim_h3_resolution)

        self.assertEqual(m1_geoid, m2_geoid, "both vehicles should be at the same location")
        vehicles_at_location = sim.v_locations[m1_geoid]
        self.assertEqual(len(vehicles_at_location), 2)
        self.assertIn(self.mock_veh_1.id, vehicles_at_location)
        self.assertIn(self.mock_veh_2.id, vehicles_at_location)

    # mock stuff
    class MockRoadNetwork(RoadNetwork):

        def route(self, origin: Position, destination: Position) -> Route:
            pass

        def update(self, sim_time: int) -> RoadNetwork:
            pass

        def geoid_to_position(self, coordinate: Coordinate) -> Position:
            return coordinate

        def position_to_geoid(self, position: Position) -> Coordinate:
            return position

        def geoid_within_geofence(self, coordinate: Coordinate) -> bool:
            return True

        def position_within_geofence(self, position: Position) -> bool:
            return True

        def geoid_within_simulation(self, coordinate: Coordinate) -> bool:
            return True

        def position_within_simulation(self, position: Position) -> bool:
            return True

    class MockRoadNetworkBadCoordinates(MockRoadNetwork):
        def coordinate_within_geofence(self, coordinate: Coordinate) -> bool:
            return False

        def position_within_geofence(self, position: Position) -> bool:
            return False

        def coordinate_within_simulation(self, coordinate: Coordinate) -> bool:
            return False

        def position_within_simulation(self, position: Position) -> bool:
            return False

    class MockEngine(Engine):
        """
        i haven't made instances of Engine yet. 20191106-rjf
        """

        def route_fuel_cost(self, route: Route) -> KwH:
            return len(route.route)

        def route_step_fuel_cost(self, route_step: RouteStep) -> KwH:
            return 1.0

    mock_veh_1 = Vehicle("m1",
                         MockEngine(),
                         Battery.build("test_battery", 100),
                         Coordinate(0, 0),
                         h3.geo_to_h3(0, 0, 11))

    mock_veh_2 = Vehicle("m2",
                         MockEngine(),
                         Battery.build("test_battery_2", 1000),
                         Coordinate(0, 0),
                         h3.geo_to_h3(0, 0, 11))

    mock_station_1 = Station("s1", Coordinate(10, 0), h3.geo_to_h3(10, 0, 11))
    mock_station_2 = Station("s2", Coordinate(0, 10), h3.geo_to_h3(0, 10, 11))

    mock_base_1 = Base("b1", Coordinate(3, 3), h3.geo_to_h3(3, 3, 11))
    mock_base_2 = Base("b2", Coordinate(7, 7), h3.geo_to_h3(7, 7, 11))
