import copy
from typing import cast, Optional
from unittest import TestCase, skip

from h3 import h3

from hive.model.base import Base
from hive.model.energy.charger import Charger
from hive.model.energy.energysource import EnergySource
from hive.model.energy.energytype import EnergyType
from hive.model.energy.powertrain import Powertrain
from hive.model.request import Request
from hive.model.roadnetwork.property_link import PropertyLink
from hive.model.station import Station
from hive.model.vehiclestate import VehicleState
from hive.model.vehicle import Vehicle

from hive.model.roadnetwork.roadnetwork import RoadNetwork
from hive.model.roadnetwork.routetraversal import Route
from hive.model.roadnetwork.link import Link
from hive.simulationstate.simulationstate import SimulationState
from hive.simulationstate.simulationstateops import initial_simulation_state
from hive.util.typealiases import *

from hive.dispatcher.greedy_dispatcher import GreedyDispatcher


class TestGreedyDispatcher(TestCase):

    def test_match_vehicle(self):
        dispatcher = GreedyDispatcher()

        somewhere = '89283470d93ffff'
        close_to_somewhere = '89283470d87ffff'
        far_from_somewhere = '89283470c27ffff'

        req = GreedyDispatcherTestAssets.mock_request(origin=somewhere)
        close_veh = GreedyDispatcherTestAssets.mock_vehicle(vehicle_id='close_veh', geoid=close_to_somewhere)
        far_veh = GreedyDispatcherTestAssets.mock_vehicle(vehicle_id='far_veh', geoid=far_from_somewhere)
        sim = GreedyDispatcherTestAssets.mock_empty_sim().add_request(req).add_vehicle(close_veh).add_vehicle(far_veh)

        dispatcher, instructions = dispatcher.generate_instructions(sim)

        self.assertIsNotNone(instructions, "Should have generated at least one instruction")
        self.assertEqual(instructions[0].action,
                         VehicleState.DISPATCH_TRIP,
                         "Should have instructed vehicle to dispatch")
        self.assertEqual(instructions[0].vehicle_id,
                         close_veh.id,
                         "Should have picked closest vehicle")

    def test_charge_vehicle(self):
        dispatcher = GreedyDispatcher()

        somewhere = '89283470d93ffff'
        somewhere_else = '89283470d87ffff'

        veh = GreedyDispatcherTestAssets.mock_vehicle(vehicle_id='test_veh', geoid=somewhere)
        low_battery = EnergySource.build("", EnergyType.ELECTRIC, 50, 50, 0.1)
        veh_low_battery = veh.battery_swap(low_battery)
        station = GreedyDispatcherTestAssets.mock_station(station_id='test_station', geoid=somewhere_else)
        sim = GreedyDispatcherTestAssets.mock_empty_sim().add_vehicle(veh_low_battery).add_station(station)

        dispatcher, instructions = dispatcher.generate_instructions(sim)

        self.assertIsNotNone(instructions, "Should have generated at least one instruction")
        self.assertEqual(instructions[0].action,
                         VehicleState.DISPATCH_STATION,
                         "Should have instructed vehicle to dispatch to station")
        self.assertEqual(instructions[0].location,
                         station.geoid,
                         "Should have picked location equal to test_station")

    def test_idle_time_out(self):
        dispatcher = GreedyDispatcher()

        somewhere = '89283470d93ffff'
        somewhere_else = '89283470d87ffff'

        veh = GreedyDispatcherTestAssets.mock_vehicle(vehicle_id='test_veh', geoid=somewhere)
        stationary_vehicle = veh._replace(idle_time_steps=1000)
        base = GreedyDispatcherTestAssets.mock_base(base_id='test_base', geoid=somewhere_else)
        sim = GreedyDispatcherTestAssets.mock_empty_sim().add_vehicle(stationary_vehicle).add_base(base)

        dispatcher, instructions = dispatcher.generate_instructions(sim)

        self.assertIsNotNone(instructions, "Should have generated at least one instruction")
        self.assertEqual(instructions[0].action,
                         VehicleState.DISPATCH_BASE,
                         "Should have instructed vehicle to dispatch to base")
        self.assertEqual(instructions[0].location,
                         base.geoid,
                         "Should have picked location equal to test_station")


class GreedyDispatcherTestAssets:
    class MockRoadNetwork(RoadNetwork):

        def route(self, origin: PropertyLink, destination: PropertyLink) -> Route:
            start = origin.link.start
            end = destination.link.end
            return (PropertyLink("mpl", Link("ml", start, end), 1, 1, 1),)

        def property_link_from_geoid(self, geoid: GeoId) -> Optional[PropertyLink]:
            return PropertyLink("mpl", Link("ml", geoid, geoid), 1, 1, 1)

        def update(self, sim_time: Time) -> RoadNetwork:
            return self

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

    class MockPowertrain(Powertrain):
        def get_id(self) -> PowertrainId:
            return "mock_powertrain"

        def get_energy_type(self) -> EnergyType:
            return EnergyType.ELECTRIC

        def energy_cost(self, route: Route) -> Kw:
            return len(route)

    @classmethod
    def mock_request(cls,
                     request_id="r1",
                     origin: GeoId = h3.geo_to_h3(39.74, -105, 15),
                     destination: GeoId = h3.geo_to_h3(39.76, -105, 15),
                     passengers: int = 2) -> Request:
        return Request.build(
            request_id=request_id,
            origin=origin,
            destination=destination,
            departure_time=28800,
            cancel_time=29400,
            passengers=passengers
        )

    @classmethod
    def mock_vehicle(cls,
                     vehicle_id="m1",
                     geoid: GeoId = h3.geo_to_h3(39.75, -105, 15)) -> Vehicle:
        mock_powertrain = cls.MockPowertrain()
        mock_property_link = cls.MockRoadNetwork().property_link_from_geoid(geoid)
        mock_veh = Vehicle(vehicle_id,
                           mock_powertrain.get_id(),
                           "",
                           EnergySource.build("", EnergyType.ELECTRIC, 40, 40, 1),
                           geoid,
                           mock_property_link,
                           )
        return mock_veh

    @classmethod
    def mock_station(cls,
                     station_id="s1",
                     geoid: GeoId = h3.geo_to_h3(39.75, -105.01, 15)) -> Station:
        return Station.build(station_id, geoid, {Charger.LEVEL_2: 5})

    @classmethod
    def mock_base(cls, base_id="b1", geoid: GeoId = h3.geo_to_h3(39.73, -105, 15)) -> Base:
        return Base.build(base_id, geoid, None, 5)

    @classmethod
    def mock_empty_sim(cls) -> SimulationState:
        sim, failures = initial_simulation_state(cls.MockRoadNetwork())
        assert len(failures) == 0, f"default sim used for tests had failures:\n {failures}"
        return sim
