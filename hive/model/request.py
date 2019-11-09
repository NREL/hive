from __future__ import annotations
from typing import NamedTuple, Optional, Tuple
from hive.model.coordinate import Coordinate
from hive.model.passenger import Passenger, create_passenger_id
# from hive.model.vehicle import Vehicle
from hive.util.typealiases import *


class Request(NamedTuple):
    """
    a ride hail request which is alive in the simulation but not yet serviced.
    it should only exist if the current sim time >= self.departure_time.
    it should be removed once the current sim time == self.cancel_time.
    if a vehicle has been dispatched to service this Request, then it should
    """
    id: RequestId
    origin: Coordinate
    destination: Coordinate
    departure_time: int
    cancel_time: int
    passengers: Tuple[Passenger]
    dispatched_vehicle: Optional[VehicleId] = None
    dispatched_vehicle_time: Optional[int] = None

    @classmethod
    def build(cls, _id: RequestId, _origin: Coordinate, _destination: Coordinate, _departure_time: int,
              _cancel_time: int, _passengers: int) -> Request:
        """
        constructor which tests assertions about the arguments for this Request
        :param _id:
        :param _origin:
        :param _destination:
        :param _departure_time:
        :param _cancel_time:
        :param _passengers:
        :return:
        """
        assert (_departure_time >= 0)
        assert (_cancel_time >= 0)
        assert (_passengers > 0)
        request_as_passengers = [
            Passenger(create_passenger_id(_id, pass_idx), _origin, _destination, _departure_time,
                      _id)
            for
            pass_idx in range(0, _passengers)]
        return cls(_id, _origin, _destination, _departure_time, _cancel_time, request_as_passengers)

    @classmethod
    def from_string(cls, string) -> Optional[Request]:
        """
        parse a string from an input file to construct a Request
        :param string: something like a CSV row or something like that. perhaps Regex?
        :return: a Request,
        """
        # todo: parses a string, calls cls.build() with the result
        raise NotImplementedError(f"yo, this doesn't exist brah, but, nice string anyway: {string}")

    def assign_dispatched_vehicle(self, vehicle_id: VehicleId, current_time: int) -> Request:
        """
        allows the dispatcher to update the request that a vehicle has been dispatched to them.
        this does not signal that the vehicle is guaranteed to pick them up.
        :param vehicle_id: the vehicle that is planning to service the request
        :param current_time: the current simulation time
        :return: the updated Request
        """
        return self._replace(dispatched_vehicle=vehicle_id, dispatched_vehicle_time=current_time)

    def update_origin(self, lat, lon) -> Request:
        """
        used to override a request's origin location as the centroid of the spatial grid,
        to make guarantees about what conditions will make requests overlap with vehicles.
        :param lat:
        :param lon:
        :return:
        """
        return self._replace(
            origin=Coordinate(lat, lon)
        )
