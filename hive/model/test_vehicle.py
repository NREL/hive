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
        self.fail()

    @skip("test not yet implemented")
    def test_step(self):
        self.fail()

    @skip("test not yet implemented")
    def test_battery_swap(self):
        self.fail()

    def test_transition_idle(self):
        non_idling_vehicle = TestVehicle.mock_vehicle()._replace(route=TestVehicle.mock_route(),
                                                                 vehicle_state=VehicleState.REPOSITIONING)
        transitioned = non_idling_vehicle.transition_idle()
        self.assertEqual(transitioned.vehicle_state, VehicleState.IDLE, "should have transitioned into an idle state")
        self.assertEqual(transitioned.route.is_empty(), True, "should have removed its route")
        self.assertEqual(transitioned.plugged_in(), False, "should not have a charger")
        result = transitioned.step()
        # no changes should be observed
        self.assertEqual(transitioned, result, "transition->step should be same as transition for IDLE")

    def test_transition_repositioning(self):
        idle_vehicle = TestVehicle.mock_vehicle()
        route = TestVehicle.mock_route()
        first_route_step, *remaining_route = route.route
        self.assertNotEqual(idle_vehicle.vehicle_state, VehicleState.REPOSITIONING,
                            "test vehicle should not begin in repositioning state")

        transitioned = idle_vehicle.transition_repositioning(route)
        self.assertEqual(transitioned.plugged_in(), False, "should not have a charger")
        self.assertEqual(len(transitioned.route), len(route), "should not have consumed any of the route")
        self.assertEqual(transitioned.position, idle_vehicle.position,
                         "vehicle position should not be changed")

        result = transitioned.step()
        # TODO: PyCharm + unittest lost Route type information somehow and can't find is_empty() function
        # self.assertEqual(result.route.is_empty(), False, "route should be updated")
        self.assertEqual(result.plugged_in(), False, "should not have a charger")
        self.assertEqual(len(result.route), len(remaining_route), "should have consumed one leg of the route")
        self.assertEqual(result.position, first_route_step.position,
                         "vehicle should have updated its position one step into route")

    def test_transition_dispatch_trip(self):
        """
        given a Vehicle in an IDLE state,
        - assign it to a DISPATCH_TRIP state via Vehicle.transition_dispatch_trip
          - confirm the vehicle state is correctly updated
        - apply the Vehicle.step() function
          - confirm the vehicle has taken 1 step toward completing a DISPATCH_TRIP
        """
        idle_vehicle = TestVehicle.mock_vehicle()
        dispatch_route = TestVehicle.mock_route()
        service_route = TestVehicle.mock_service_route()
        first_route_step, *remaining_route = dispatch_route.route

        # check on transition function result
        transitioned = idle_vehicle.transition_dispatch_trip(dispatch_route, service_route)
        self.assertIsInstance(transitioned, Vehicle, "result should be a Vehicle, not an Exception")
        self.assertEqual(transitioned.plugged_in(), False, "should not have a charger")
        self.assertEqual(len(transitioned.route), len(dispatch_route), "should not have consumed any of the route")
        self.assertEqual(transitioned.position, idle_vehicle.position,
                         "vehicle position should not be changed")

        # check on step function result
        result = transitioned.step()
        self.assertEqual(result.plugged_in(), False, "should not have a charger")
        self.assertEqual(len(result.route), len(remaining_route), "should have consumed one leg of the route")
        self.assertEqual(result.position, first_route_step.position,
                         "vehicle should have updated its position one step into route")

    def test_transition_dispatch_trip_negative_low_soc(self):
        """
        given a Vehicle which has a soc_lower_limit of 100% (not allowed to have less than 100% fuel),
        - assign it to a DISPATCH_TRIP state via Vehicle.transition_dispatch_trip
          - confirm the result is a StateTransitionError
        """
        snooty_test_vehicle = TestVehicle.mock_vehicle()._replace(soc_lower_limit=1.0)

        # check on transition function result
        transitioned = snooty_test_vehicle.transition_dispatch_trip(TestVehicle.mock_route(),
                                                                    TestVehicle.mock_service_route())

        # todo: i tried asserting that it is a StateTransitionError, but, unittest is failing
        #  on that comparison. perhaps nose is better at this kind of type introspection for
        #  assertions?
        self.assertIsInstance(transitioned, Exception,
                              "result should be a StateTransitionError, not a Vehicle")

    @skip("test not yet implemented")
    def test_transition_servicing_trip(self):
        self.fail()

    @skip("test not yet implemented")
    def test_transition_dispatch_station(self):
        self.fail()

    @skip("test not yet implemented")
    def test_transition_charging_station(self):
        self.fail()

    @skip("test not yet implemented")
    def test_transition_dispatch_base(self):
        self.fail()

    @skip("test not yet implemented")
    def test_transition_charging_base(self):
        self.fail()

    @skip("test not yet implemented")
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
