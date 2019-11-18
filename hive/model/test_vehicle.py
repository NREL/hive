from unittest import TestCase, skip

from h3 import h3

from hive.model.energysource import EnergySource
from hive.model.coordinate import Coordinate
from hive.model.request import Request
from hive.model.vehicle import Vehicle
from hive.model.vehiclestate import VehicleState
from hive.roadnetwork.route import Route
from hive.roadnetwork.link import Link


class TestVehicle(TestCase):
    def test_has_passengers(self):
        self.assertEqual(TestVehicle.mock_vehicle().has_passengers(), False, "should have no passengers")
        updated_vehicle = TestVehicle.mock_vehicle().add_passengers(TestVehicle.mock_request().passengers)
        self.assertEqual(updated_vehicle.has_passengers(), True, "should have passengers")

    def test_has_route(self):
        self.assertEqual(TestVehicle.mock_vehicle().has_route(), False, "should have no route")
        updated_vehicle = TestVehicle.mock_vehicle()._replace(route=TestVehicle.mock_route())
        self.assertEqual(updated_vehicle.has_route(), True, "should have a route")

    @skip("test not yet implemented")
    def test_add_passengers(self):
        no_pass_veh = TestVehicle.mock_vehicle()
        mock_request = TestVehicle.mock_request()

        self.assertEqual(no_pass_veh.has_passengers(), False)
        with_pass_veh = no_pass_veh.add_passengers(mock_request.passengers)
        self.assertEqual(len(with_pass_veh.passengers), len(mock_request.passengers))

    @skip("test not yet implemented")
    def test_battery_swap(self):
        self.fail()

    def test_transition_idle(self):
        non_idling_vehicle = TestVehicle.mock_vehicle()._replace(route=TestVehicle.mock_route(),
                                                                 vehicle_state=VehicleState.REPOSITIONING)
        transitioned = non_idling_vehicle.transition(VehicleState.IDLE)
        self.assertEqual(transitioned.vehicle_state, VehicleState.IDLE, "should have transitioned into an idle state")

    def test_transition_repositioning(self):
        idle_vehicle = TestVehicle.mock_vehicle()
        self.assertNotEqual(idle_vehicle.vehicle_state, VehicleState.REPOSITIONING,
                            "test vehicle should not begin in repositioning state")

        transitioned = idle_vehicle.transition(VehicleState.REPOSITIONING)
        self.assertEqual(transitioned.position, idle_vehicle.position,
                         "vehicle position should not be changed")

    def test_transition_dispatch_trip(self):
        """
        given a Vehicle in an IDLE state,
        - assign it to a DISPATCH_TRIP state via Vehicle.transition_dispatch_trip
          - confirm the vehicle state is correctly updated
        """
        idle_vehicle = TestVehicle.mock_vehicle()

        # check on transition function result
        transitioned = idle_vehicle.transition(VehicleState.DISPATCH_TRIP)
        self.assertIsInstance(transitioned, Vehicle, "result should be a Vehicle, not an Exception")
        self.assertEqual(transitioned.position, idle_vehicle.position,
                         "vehicle position should not be changed")

    def test_transition_servicing_trip(self):
        idle_vehicle = TestVehicle.mock_vehicle()

        transitioned = idle_vehicle.transition(VehicleState.SERVICING_TRIP)

        self.assertIsInstance(transitioned, Vehicle, "result should be a Vehicle, not an Exception")
        self.assertEqual(transitioned.position, idle_vehicle.position,
                         "vehicle position should not be changed")

    def test_transition_dispatch_station(self):
        idle_vehicle = TestVehicle.mock_vehicle()

        transitioned = idle_vehicle.transition(VehicleState.DISPATCH_TRIP)
        self.assertIsInstance(transitioned, Vehicle, "result should be a Vehicle, not an Exception")
        self.assertEqual(transitioned.position, idle_vehicle.position,
                         "vehicle position should not be changed")

    def test_transition_charging_station(self):
        idle_vehicle = TestVehicle.mock_vehicle()

        transitioned = idle_vehicle.transition(VehicleState.CHARGING_STATION)
        self.assertIsInstance(transitioned, Vehicle, "result should be a Vehicle, not an Exception")
        self.assertEqual(transitioned.position, idle_vehicle.position,
                         "vehicle position should not be changed")

    def test_transition_dispatch_base(self):
        idle_vehicle = TestVehicle.mock_vehicle()

        transitioned = idle_vehicle.transition(VehicleState.DISPATCH_BASE)
        self.assertIsInstance(transitioned, Vehicle, "result should be a Vehicle, not an Exception")
        self.assertEqual(transitioned.position, idle_vehicle.position,
                         "vehicle position should not be changed")

    def test_transition_charging_base(self):
        idle_vehicle = TestVehicle.mock_vehicle()

        transitioned = idle_vehicle.transition(VehicleState.CHARGING_BASE)
        self.assertIsInstance(transitioned, Vehicle, "result should be a Vehicle, not an Exception")
        self.assertEqual(transitioned.position, idle_vehicle.position,
                         "vehicle position should not be changed")

    def test_transition_reserve_base(self):
        idle_vehicle = TestVehicle.mock_vehicle()

        transitioned = idle_vehicle.transition(VehicleState.RESERVE_BASE)
        self.assertIsInstance(transitioned, Vehicle, "result should be a Vehicle, not an Exception")
        self.assertEqual(transitioned.position, idle_vehicle.position,
                         "vehicle position should not be changed")

    def test_can_transition_good(self):
        mock_request = TestVehicle.mock_request()
        idle_veh = TestVehicle.mock_vehicle()
        veh_serving_trip = idle_veh.transition(VehicleState.SERVICING_TRIP)
        veh_w_pass = veh_serving_trip.add_passengers(mock_request.passengers)

        veh_can_trans =veh_w_pass.can_transition(VehicleState.SERVICING_TRIP)

        self.assertEqual(veh_can_trans, True)

    def test_can_transition_bad(self):
        mock_request = TestVehicle.mock_request()
        idle_veh = TestVehicle.mock_vehicle()
        veh_serving_trip = idle_veh.transition(VehicleState.SERVICING_TRIP)
        veh_w_pass = veh_serving_trip.add_passengers(mock_request.passengers)

        veh_can_trans = veh_w_pass.can_transition(VehicleState.IDLE)

        self.assertEqual(veh_can_trans, False)

    @classmethod
    def mock_vehicle(cls) -> Vehicle:
        return Vehicle("test_vehicle",
                       "test_engine",
                       EnergySource.build("test_battery", 100),
                       Coordinate(0, 0),
                       h3.geo_to_h3(0, 0, 11)
                       )

    @classmethod
    def mock_request(cls) -> Request:
        return Request.build("test_request",
                             origin=Coordinate(0, 0),
                             destination=Coordinate(10, 10),
                             origin_geoid=h3.geo_to_h3(0, 0, 11),
                             destination_geoid=h3.geo_to_h3(10, 10, 11),
                             departure_time=0,
                             cancel_time=10,
                             passengers=2)

    @classmethod
    def mock_route(cls) -> Route:
        return Route(route=(Link(Coordinate(0, 5), 5),
                            Link(Coordinate(5, 5), 5),
                            Link(Coordinate(5, 10), 5),
                            Link(Coordinate(10, 10), 5)),
                     total_distance=20,
                     total_travel_time=4)

