from __future__ import annotations
from typing import NamedTuple, Optional
from hive.model.passenger import Passenger, create_passenger_id
from hive.util.typealiases import *


class Request(NamedTuple):
    """
    a ride hail request which is alive in the simulation but not yet serviced.
    it should only exist if the current sim time >= self.departure_time.
    it should be removed once the current sim time == self.cancel_time.
    if a vehicle has been dispatched to service this Request, then it should
    """
    id: RequestId
    origin: GeoId
    destination: GeoId
    departure_time: int
    cancel_time: int
    passengers: Tuple[Passenger]
    dispatched_vehicle: Optional[VehicleId] = None
    dispatched_vehicle_time: Optional[int] = None

    @classmethod
    def build(cls,
              request_id: RequestId,
              origin: GeoId,
              destination: GeoId,
              departure_time: int,
              cancel_time: int,
              passengers: int) -> Request:
        """
        constructor which tests assertions about the arguments for this Request
        :param request_id:
        :param origin:
        :param destination:
        :param departure_time:
        :param cancel_time:
        :param passengers:
        :return:
        """
        assert (departure_time >= 0)
        assert (cancel_time >= 0)
        assert (passengers > 0)
        request_as_passengers = [
            Passenger(create_passenger_id(request_id, pass_idx), origin, destination, departure_time)
            for
            pass_idx in range(0, passengers)]
        return Request(request_id,
                       origin,
                       destination,
                       departure_time,
                       cancel_time,
                       tuple(request_as_passengers))

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

    def update_origin(self, geoid: GeoId) -> Request:
        """
        used to override a request's origin location as the centroid of the spatial grid,
        to make guarantees about what conditions will make requests overlap with vehicles.
        :param geoid:
        :return:
        """
        return self._replace(
            origin=geoid
        )
