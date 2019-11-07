import unittest

from hive.util.typealiases import KwH
from hive.model.battery import Battery
from hive.model.coordinate import Coordinate
from hive.model.engine import Engine
from hive.model.request import Request
from hive.model.vehicle import Vehicle
from hive.model.passenger import create_passenger_id
from hive.roadnetwork.roadnetwork import Route, RouteStep


class MyTestCase(unittest.TestCase):
    request_id = "test"
    origin = Coordinate(lat=0.0, lon=0.0)
    destination = Coordinate(lat=3.0, lon=4.0)
    departure_time = 28800
    cancel_time = 29400
    passengers = 2
    request = Request.build(
        _id=request_id,
        _origin=origin,
        _destination=destination,
        _departure_time=departure_time,
        _cancel_time=cancel_time,
        _passengers=passengers
    )

    class FakeEngine(Engine):

        def route_fuel_cost(self, route: Route) -> KwH:
            return 1.0

        def route_step_fuel_cost(self, route_step: RouteStep) -> KwH:
            return 1.0

    def test_request_constructor(self):
        """
        the constructed request should not modify its arguments
        """
        self.assertEqual(self.request.id, self.request_id)
        self.assertEqual(self.request.origin, self.origin)
        self.assertEqual(self.request.destination, self.destination)
        self.assertEqual(self.request.departure_time, self.departure_time)
        self.assertEqual(self.request.cancel_time, self.cancel_time)
        self.assertEqual(self.request.passengers, self.passengers)

    def test_request_create_passengers(self):
        """
        turning a request into passengers of a vehicle
        """
        battery = Battery.build("test_battery", 100.0)
        engine = self.FakeEngine()
        vehicle = Vehicle(id="test_vehicle", position=Coordinate(0, 0), battery=battery, engine=engine)
        request_as_passengers = self.request.as_passengers(vehicle)
        updated_vehicle = vehicle.add_passengers(request_as_passengers)

        # should now have 2 passengers
        self.assertEqual(len(updated_vehicle.passengers), 2)

        # the passengers should match our request and have unique names
        for i in range(0, 2):

            # the passengers should have the correct ids
            target_passenger_id = create_passenger_id(self.request_id, i)
            passenger = updated_vehicle.passengers[target_passenger_id]
            self.assertEqual(passenger.id, target_passenger_id)

            # passenger details should be consistent with request
            self.assertEqual(passenger.origin, self.request.origin)
            self.assertEqual(passenger.destination, self.request.destination)
            self.assertEqual(passenger.departure_time, self.request.departure_time)

            # the current vehicle should be known to each passenger
            self.assertEqual(passenger.vehicle_id, vehicle.id)


if __name__ == '__main__':
    unittest.main()
