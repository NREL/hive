from __future__ import annotations
from typing import NamedTuple, Optional, Dict, Union
from hive.model.passenger import Passenger, create_passenger_id
from hive.model.roadnetwork.roadnetwork import RoadNetwork
from hive.util.typealiases import *

from h3 import h3

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
    departure_time: SimTime
    cancel_time: SimTime
    passengers: Tuple[Passenger]
    dispatched_vehicle: Optional[VehicleId] = None
    dispatched_vehicle_time: Optional[SimTime] = None

    @classmethod
    def build(cls,
              request_id: RequestId,
              origin: GeoId,
              destination: GeoId,
              departure_time: SimTime,
              cancel_time: SimTime,
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
    def from_row(cls, row: Dict[str, str], road_network: RoadNetwork) -> Union[IOError, Request]:
        """
        takes a csv row and turns it into a Request
        :param row: a row as interpreted by csv.DictReader
        :param road_network: the road network loaded for this simulation
        :return: a Request, or an error
        """
        if 'request_id' not in row:
            return IOError("cannot load a request without a 'request_id'")
        elif 'origin_x' not in row:
            return IOError("cannot load a request without an 'origin_x' value")
        elif 'origin_y' not in row:
            return IOError("cannot load a request without an 'origin_y' value")
        elif 'destination_x' not in row:
            return IOError("cannot load a request without a 'destination_x' value")
        elif 'destination_y' not in row:
            return IOError("cannot load a request without a 'destination_y' value")
        elif 'departure_time' not in row:
            return IOError("cannot load a request without a 'departure_time'")
        elif 'cancel_time' not in row:
            return IOError("cannot load a request without a 'cancel_time'")
        elif 'passengers' not in row:
            return IOError("cannot load a request without a number of 'passengers'")
        else:
            request_id = row['request_id']
            try:
                o_x, o_y = float(row['origin_x']), float(row['origin_y'])
                d_x, d_y = float(row['destination_x']), float(row['destination_y'])
                o_geoid = h3.geo_to_h3(o_x, o_y, road_network.sim_h3_resolution)
                d_geoid = h3.geo_to_h3(d_x, d_y, road_network.sim_h3_resolution)
                departure_time = int(row['departure_time'])
                cancel_time = int(row['cancel_time'])
                passengers = int(row['passengers'])
                return Request.build(
                    request_id=request_id,
                    origin=o_geoid,
                    destination=d_geoid,
                    departure_time=departure_time,
                    cancel_time=cancel_time,
                    passengers=passengers
                )
            except ValueError:
                return IOError(f"unable to parse request {request_id} from row due to invalid value(s): {row}")

    def assign_dispatched_vehicle(self, vehicle_id: VehicleId, current_time: SimTime) -> Request:
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
