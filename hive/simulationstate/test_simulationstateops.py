from unittest import TestCase
from typing import Tuple

from hive.model.battery import Battery
from hive.model.coordinate import Coordinate
from hive.model.engine import Engine
from hive.model.vehicle import Vehicle
from hive.roadnetwork.position import Position
from hive.roadnetwork.roadnetwork import RoadNetwork
from hive.roadnetwork.route import Route
from hive.roadnetwork.routestep import RouteStep
from hive.simulationstate.simulationstate import SimulationState
from hive.simulationstate.simulationstateops import initial_simulation_state
from hive.util.typealiases import *
from hive.util.exception import *
from h3 import h3


class TestSimulationStateOps(TestCase):
    def test_initial_simulation_state(self):

        # build sim state
        sim, failures = initial_simulation_state(
            (self.mock_veh_1, self.mock_veh_2),
            tuple(),
            tuple(),
            self.MockRoadNetwork()
        )

        # head check
        self.assertIsInstance(sim, SimulationState)
        self.assertEqual(len(failures), 0)

        # vehicles were properly geo-coded (reverse lookup)
        m1_coord = sim.road_network.position_to_coordinate(self.mock_veh_1.position)
        m2_coord = sim.road_network.position_to_coordinate(self.mock_veh_2.position)
        m1_geoid = h3.geo_to_h3(m1_coord.lat, m1_coord.lon, sim.sim_h3_resolution)
        m2_geoid = h3.geo_to_h3(m2_coord.lat, m2_coord.lon, sim.sim_h3_resolution)
        self.assertIn(self.mock_veh_1.id, sim.v_locations[m1_geoid])
        self.assertIn(self.mock_veh_2.id, sim.v_locations[m2_geoid])

    # mock stuff
    class MockRoadNetwork(RoadNetwork):

        def route(self, origin: Position, destination: Position) -> Route:
            pass

        def update(self, sim_time: int) -> RoadNetwork:
            pass

        def coordinate_to_position(self, coordinate: Coordinate) -> Position:
            return coordinate

        def position_to_coordinate(self, position: Position) -> Coordinate:
            return position

        def coordinate_within_geofence(self, coordinate: Coordinate) -> bool:
            return True

        def position_within_geofence(self, position: Position) -> bool:
            return True

        def coordinate_within_simulation(self, coordinate: Coordinate) -> bool:
            return True

        def position_within_simulation(self, position: Position) -> bool:
            return True

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
                         Coordinate(0, 0))
    mock_veh_2 = Vehicle("m2",
                         MockEngine(),
                         Battery.build("test_battery_2", 1000),
                         Coordinate(10, 10))
