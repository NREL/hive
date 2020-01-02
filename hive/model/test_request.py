import unittest
from csv import DictReader

from hive.model.energy.energytype import EnergyType
from hive.model.roadnetwork.haversine_roadnetwork import HaversineRoadNetwork
from hive.model.roadnetwork.property_link import PropertyLink
from hive.model.energy.energysource import EnergySource
from hive.model.request import Request
from hive.model.vehicle import Vehicle
from hive.model.passenger import create_passenger_id
from hive.model.roadnetwork.link import Link
from hive.util.units import unit
from h3 import h3


class MyTestCase(unittest.TestCase):
    request_id = "test"
    origin = h3.geo_to_h3(0, 0, res=11)
    destination = h3.geo_to_h3(3, 4, res=11)
    departure_time = 28800
    cancel_time = 29400
    passengers = 2
    request = Request.build(
        request_id=request_id,
        origin=origin,
        destination=destination,
        departure_time=departure_time,
        cancel_time=cancel_time,
        passengers=passengers
    )

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
        battery = EnergySource.build("unused",
                                     EnergyType.ELECTRIC,
                                     100.0*unit.kilowatthour,
                                     )
        vehicle = Vehicle(id="test_vehicle",
                          powertrain_id="fake_powertrain_id",
                          powercurve_id="fake",
                          energy_source=battery,
                          property_link=PropertyLink(
                              "test",
                              Link("test", h3.geo_to_h3(0, 0, 15), h3.geo_to_h3(1, 1, 15)),
                              10,
                              10,
                              1))
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
            self.assertEqual(passenger.origin, self.request.origin)
            self.assertEqual(passenger.destination, self.request.destination)
            self.assertEqual(passenger.departure_time, self.request.departure_time)

            # the current vehicle should be known to each passenger
            self.assertEqual(passenger.vehicle_id, vehicle.id)

    def test_from_row(self):
        source = """request_id,o_lat,o_lon,d_lat,d_lon,departure_time,cancel_time,passengers
        1_a,31.2074449,121.4294263,31.2109091,121.4532226,61200,61800,4
        """
        row = next(DictReader(source.split()))
        rn = HaversineRoadNetwork()
        req = Request.from_row(row, rn)
        self.assertEqual(req.id, "1_a")
        self.assertEqual(req.origin, h3.geo_to_h3(31.2074449,121.4294263,rn.sim_h3_resolution))
        self.assertEqual(req.destination, h3.geo_to_h3(31.2109091,121.4532226,rn.sim_h3_resolution))
        self.assertEqual(req.departure_time, 61200)
        self.assertEqual(req.cancel_time, 61800)
        self.assertEqual(len(req.passengers), 4)


if __name__ == '__main__':
    unittest.main()
