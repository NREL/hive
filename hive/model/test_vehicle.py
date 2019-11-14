from unittest import TestCase, skip

from hive.exception import StateTransitionError
from hive.model.battery import Battery
from hive.model.coordinate import Coordinate
from hive.model.engine import Engine
from hive.model.vehicle import Vehicle
from hive.model.request import Request
from hive.model.vehiclestate import VehicleState
from hive.roadnetwork.route import Route
from hive.roadnetwork.routestep import RouteStep
from hive.util.typealiases import KwH
from hive.util.tuple import head_tail


class TestVehicle(TestCase):
    class MockEngine(Engine):
        """
        i haven't made instances of Engine yet. 20191106-rjf
        """

        def route_fuel_cost(self, route: Route) -> KwH:
            return len(route.route)

        def route_step_fuel_cost(self, route_step: RouteStep) -> KwH:
            return 1.0

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


    #TODO: Consider moving this test to the SimulationState space
    @skip("test not yet implemented")
    def test_step(self):
        self.fail()

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

    #TODO: Consider moving this test to the SimulationState space
    @skip("Test needs updating")
    def test_transition_dispatch_trip_negative_low_soc(self):
        """
        given a Vehicle which has a soc_lower_limit of 100% (not allowed to have less than 100% fuel),
        - assign it to a DISPATCH_TRIP state via Vehicle.transition_dispatch_trip
          - confirm the result is a StateTransitionError
        """
        snooty_test_vehicle = TestVehicle.mock_vehicle()._replace(soc_lower_limit=1.0)

        # check on transition function result
        transitioned = snooty_test_vehicle.transition_dispatch_trip(
                            TestVehicle.mock_route(),
                            TestVehicle.mock_service_route())

        self.assertTrue(transitioned is None)

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

    @skip("test not yet implemented")
    def test_transition_charging_base(self):
        idle_vehicle = TestVehicle.mock_vehicle()

        transitioned = idle_vehicle.transition(VehicleState.CHARGING_BASE)
        self.assertIsInstance(transitioned, Vehicle, "result should be a Vehicle, not an Exception")
        self.assertEqual(transitioned.position, idle_vehicle.position,
                         "vehicle position should not be changed")

    @skip("test not yet implemented")
    def test_transition_reserve_base(self):
        idle_vehicle = TestVehicle.mock_vehicle()

        transitioned = idle_vehicle.transition(VehicleState.RESERVE_BASE)
        self.assertIsInstance(transitioned, Vehicle, "result should be a Vehicle, not an Exception")
        self.assertEqual(transitioned.position, idle_vehicle.position,
                         "vehicle position should not be changed")

    @classmethod
    def mock_vehicle(cls) -> Vehicle:
        return Vehicle("test_vehicle",
                       cls.MockEngine(),
                       Battery.build("test_battery", 100),
                       Coordinate(0, 0))

    @classmethod
    def mock_request(cls) -> Request:
        return Request.build("test_request",
                             _origin=Coordinate(0, 0),
                             _destination=Coordinate(10, 10),
                             _departure_time=0,
                             _cancel_time=10,
                             _passengers=2)

    @classmethod
    def mock_route(cls) -> Route:
        return Route(route=(RouteStep(Coordinate(0, 5), 5),
                            RouteStep(Coordinate(5, 5), 5),
                            RouteStep(Coordinate(5, 10), 5),
                            RouteStep(Coordinate(10, 10), 5)),
                     total_distance=20,
                     total_travel_time=4)

    @classmethod
    def mock_service_route(cls) -> Route:
        return Route(route=(RouteStep(Coordinate(5, 10), 5),
                            RouteStep(Coordinate(5, 5), 5),
                            RouteStep(Coordinate(0, 5), 5),
                            RouteStep(Coordinate(0, 0), 5)
                            ),
                     total_distance=20,
                     total_travel_time=4)
