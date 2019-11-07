from unittest import TestCase

from hive.model.battery import Battery
from hive.model.coordinate import Coordinate
from hive.model.engine import Engine
from hive.model.vehicle import Vehicle
from hive.model.request import Request
from hive.physics.vehiclestate import VehicleState
from hive.roadnetwork.route import Route
from hive.roadnetwork.routestep import RouteStep
from hive.util.typealiases import KwH


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

    def test_add_passengers(self):
        self.fail()

    def test_default_state_behavior(self):
        self.fail()

    def test_battery_swap(self):
        self.fail()

    def test_transition_idle(self):
        non_idling_vehicle = TestVehicle.mock_vehicle()._replace(route=TestVehicle.mock_route(),
                                                                 vehicle_state=VehicleState.REPOSITIONING)
        result = non_idling_vehicle.transition_idle()
        self.assertEqual(result.vehicle_state, VehicleState.IDLE, "should have transitioned into an idle state")
        self.assertEqual(result.route.is_empty(), True, "should have removed its route")
        self.assertEqual(result.plugged_in(), False, "should not have a charger")

    def test_transition_repositioning(self):
        idle_vehicle = TestVehicle.mock_vehicle()
        route = TestVehicle.mock_route()
        first_route_step, *remaining_route = route.route
        self.assertNotEqual(idle_vehicle.vehicle_state, VehicleState.REPOSITIONING,
                            "test vehicle should not begin in repositioning state")
        result = idle_vehicle.transition_repositioning(route)
        # TODO: PyCharm + unittest lost Route type information somehow and can't find is_empty() function
        # self.assertEqual(result.route.is_empty(), False, "route should be updated")
        self.assertEqual(result.plugged_in(), False, "should not have a charger")
        self.assertEqual(len(result.route), len(remaining_route), "should have consumed one leg of the route")
        self.assertEqual(result.position, first_route_step.position,
                         "vehicle should have updated its position one step into route")

    def test_transition_dispatch_trip(self):
        self.fail()

    def test_transition_servicing_trip(self):
        self.fail()

    def test_transition_dispatch_station(self):
        self.fail()

    def test_transition_charging_station(self):
        self.fail()

    def test_transition_dispatch_base(self):
        self.fail()

    def test_transition_charging_base(self):
        self.fail()

    def test_transition_reserve_base(self):
        self.fail()

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
        return Route(route=(RouteStep(Coordinate(0, 5), 5, 0),
                            RouteStep(Coordinate(5, 5), 5, 0),
                            RouteStep(Coordinate(5, 10), 5, 0),
                            RouteStep(Coordinate(10, 10), 5, 0)),
                     total_distance=20,
                     total_travel_time=4)
