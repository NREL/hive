from unittest import TestCase

from h3 import h3

from typing import Optional

from hive.model.base import Base
from hive.model.energy.energysource import EnergySource
from hive.model.energy.energytype import EnergyType
from hive.model.energy.powercurve import Powercurve
from hive.model.energy.powertrain import Powertrain
from hive.model.roadnetwork.property_link import PropertyLink
from hive.model.roadnetwork.link import Link
from hive.model.station import Station
from hive.model.vehicle import Vehicle
from hive.model.energy.charger import Charger
from hive.model.roadnetwork.roadnetwork import RoadNetwork
from hive.model.roadnetwork.routetraversal import Route
from hive.state.simulation_state import SimulationState
from hive.state.simulation_state_ops import initial_simulation_state
from hive.util.typealiases import *
from hive.util.units import unit, kwh, s


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
            self.MockRoadNetwork(),
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

    # mock stuff
    class MockRoadNetwork(RoadNetwork):

        def route(self, origin: Link, destination: Link) -> Route:
            pass

        def property_link_from_geoid(self, geoid: GeoId) -> Optional[PropertyLink]:
            return PropertyLink.build(Link("ml", geoid, geoid), 40*(unit.kilometer/unit.hour))

        def update(self, sim_time: SimTime) -> RoadNetwork:
            pass

        def get_link(self, link_id: LinkId) -> Optional[PropertyLink]:
            pass

        def get_current_property_link(self, property_link: PropertyLink) -> Optional[PropertyLink]:
            pass

        def geoid_within_geofence(self, geoid: GeoId) -> bool:
            return True

        def link_id_within_geofence(self, link_id: LinkId) -> bool:
            return True

        def geoid_within_simulation(self, geoid: GeoId) -> bool:
            return True

        def link_id_within_simulation(self, link_id: LinkId) -> bool:
            return True

        def get_current_property_link(self, property_link: PropertyLink) -> Optional[PropertyLink]:
            raise NotImplementedError("implement if needed for testing")

    class MockRoadNetworkBadCoordinates(MockRoadNetwork):
        def geoid_within_geofence(self, geoid: GeoId) -> bool:
            return False

        def link_id_within_geofence(self, link_id: LinkId) -> bool:
            return False

        def geoid_within_simulation(self, geoid: GeoId) -> bool:
            return False

        def link_id_within_simulation(self, link_id: LinkId) -> bool:
            return False

    class MockPowertrain(Powertrain):
        def get_id(self) -> PowertrainId:
            return "mock_powertrain"

        def get_energy_type(self) -> EnergyType:
            return EnergyType.ELECTRIC

        def energy_cost(self, route: Route) -> kwh:
            return len(route)

    class MockPowercurve(Powercurve):
        """
        just adds 1 when charging
        """

        def get_id(self) -> PowercurveId:
            return "mock_powercurve"

        def get_energy_type(self) -> EnergyType:
            return EnergyType.ELECTRIC

        def refuel(self, energy_source: 'EnergySource', charger: 'Charger', duration_seconds: s = 1*unit.seconds,
                   step_size_seconds: s = 1*unit.seconds) -> 'EnergySource':
            return energy_source.load_energy(1.0*unit.kilowatthour)

    mock_powertrain = MockPowertrain()
    mock_powercurve = MockPowercurve()
    mock_geoid = h3.geo_to_h3(39.75, -105, 15)
    mock_property_link = MockRoadNetwork().property_link_from_geoid(mock_geoid)

    mock_veh_1 = Vehicle("m1",
                         mock_powertrain.get_id(),
                         mock_powercurve.get_id(),
                         EnergySource.build("test_id",
                                            EnergyType.ELECTRIC,
                                            capacity=50*unit.kilowatthour,
                                            ),
                         mock_geoid,
                         mock_property_link)

    mock_veh_2 = Vehicle("m2",
                         mock_powertrain.get_id(),
                         mock_powercurve.get_id(),
                         EnergySource.build("test_id",
                                            EnergyType.ELECTRIC,
                                            capacity=50*unit.kilowatthour,
                                            ),
                         mock_geoid,
                         mock_property_link)

    mock_station_1 = Station.build("s1", h3.geo_to_h3(39.75, -105.01, 15), {Charger.LEVEL_2: 5})
    mock_station_2 = Station.build("s2", h3.geo_to_h3(39.74, -105.01, 15), {Charger.LEVEL_2: 5})

    mock_base_1 = Base.build("b1", h3.geo_to_h3(39.73, -105, 15), None, 5)
    mock_base_2 = Base.build("b2", h3.geo_to_h3(39.76, -105, 15), None, 5)
