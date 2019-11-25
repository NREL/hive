import unittest

from hive.util.typealiases import KwH
from hive.model.energysource import EnergySource
from hive.model.coordinate import Coordinate
from hive.model.powertrain.powertrain import Powertrain
from hive.model.request import Request
from hive.model.vehicle import Vehicle
from hive.model.passenger import create_passenger_id
from hive.model.roadnetwork.routetraversal import Route
from hive.model.roadnetwork.link import Link
from h3 import h3


class MyTestCase(unittest.TestCase):
    request_id = "test"
    origin = Coordinate(lat=0.0, lon=0.0)
    destination = Coordinate(lat=3.0, lon=4.0)
    o_geoid = h3.geo_to_h3(origin.lat, origin.lon, res=11)
    d_geoid = h3.geo_to_h3(destination.lat, destination.lon, res=11)
    departure_time = 28800
    cancel_time = 29400
    passengers = 2
    request = Request.build(
        request_id=request_id,
        origin=origin,
        destination=destination,
        origin_geoid=o_geoid,
        destination_geoid=d_geoid,
        departure_time=departure_time,
        cancel_time=cancel_time,
        passengers=passengers
    )

    class FakePowertrain(Powertrain):

        def route_energy_cost(self, route: Route) -> KwH:
            return 1.0

        def segment_energy_cost(self, segment: Link) -> KwH:
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
        self.assertEqual(len(self.request.passengers), self.passengers)

    def test_request_create_passengers(self):
        """
        turning a request into passengers of a vehicle
        """
        battery = EnergySource.build("test_battery", 100.0)
        engine = self.FakePowertrain()
        vehicle = Vehicle(id="test_vehicle",
                          position=Coordinate(0, 0),
                          battery=battery,
                          engine=engine,
                          geoid=h3.geo_to_h3(0, 0, 11))
        request_as_passengers = self.request.passengers
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
            self.assertEqual(passenger.origin, self.request.o_geoid)
            self.assertEqual(passenger.destination, self.request.d_geoid)
            self.assertEqual(passenger.departure_time, self.request.departure_time)

            # the current vehicle should be known to each passenger
            self.assertEqual(passenger.vehicle_id, vehicle.id)


if __name__ == '__main__':
    unittest.main()
