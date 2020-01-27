from __future__ import annotations
from h3 import h3
from typing import NamedTuple, Optional, Dict, Union
from datetime import datetime

from hive.model.passenger import Passenger, create_passenger_id
from hive.runner.environment import Environment
from hive.util.typealiases import *



class Request(NamedTuple):
    """
    A ride hail request which is alive in the simulation but not yet serviced.
    It should only exist if the current sim time >= self.departure_time.
    It should be removed once the current sim time == self.cancel_time.
    If a vehicle has been dispatched to service this Request, then it should hold the vehicle id
    and the time that vehicle was dispatched to it.

    :param id: A unique id for the request.
    :type id: :py:obj:`RequestId`
    :param origin: The geoid of the request origin.
    :type origin: :py:obj:`GeoId`
    :param destination: The geoid of the request destination.
    :type destination: :py:obj:`GeoId`
    :param departure_time: The time of departure.
    :type departure_time: :py:obj:`SimTime`
    :param cancel_time: The time when this request will cancel.
    :type cancel_time: :py:obj:`SimTime`
    :param passengers: A tuple of passengers associated with this request.
    :type passengers: :py:obj:`Tuple[Passenger]`
    :param dispatched_vehicle: The id of the vehicle dispatched to service this request.
    :type dispatched_vehicle: :py:obj:`Optional[VehicleId]`
    :param dispatched_vehicle_time: Time time which a vehicle was dispatched for this request.
    :type dispatched_vehicle_time: :py:obj:`Optional[SimTime]`
    """
    id: RequestId
    origin: GeoId
    destination: GeoId
    departure_time: SimTime
    cancel_time: SimTime
    passengers: Tuple[Passenger, ...]
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
    def from_row(cls, row: Dict[str, str], env: Environment) -> Union[Exception, Request]:
        """
        takes a csv row and turns it into a Request

        :param row: a row as interpreted by csv.DictReader
        :param road_network: the road network loaded for this simulation
        :return: a Request, or an error
        """
        if 'request_id' not in row:
            raise IOError("cannot load a request without a 'request_id'")
        elif 'o_lat' not in row:
            raise IOError("cannot load a request without an 'o_lat' value")
        elif 'o_lon' not in row:
            raise IOError("cannot load a request without an 'o_lon' value")
        elif 'd_lat' not in row:
            raise IOError("cannot load a request without a 'd_lat' value")
        elif 'd_lon' not in row:
            raise IOError("cannot load a request without a 'd_lon' value")
        elif 'departure_time' not in row:
            raise IOError("cannot load a request without a 'departure_time'")
        elif 'cancel_time' not in row:
            raise IOError("cannot load a request without a 'cancel_time'")
        elif 'passengers' not in row:
            raise IOError("cannot load a request without a number of 'passengers'")
        else:
            request_id = row['request_id']
            try:
                o_lat, o_lon = float(row['o_lat']), float(row['o_lon'])
                d_lat, d_lon = float(row['d_lat']), float(row['d_lon'])
                o_geoid = h3.geo_to_h3(o_lat, o_lon, env.config.sim.sim_h3_resolution)
                d_geoid = h3.geo_to_h3(d_lat, d_lon, env.config.sim.sim_h3_resolution)

                if env.config.io.parse_dates:
                    try:
                        departure_dt = datetime.strptime(row['departure_time'], env.config.io.date_format)
                        cancel_dt = datetime.strptime(row['cancel_time'], env.config.io.date_format)
                    except ValueError:
                        raise IOError("Unable to parse datetime. Make sure the format matches config.io.date_format")
                    departure_time = int(departure_dt.timestamp())
                    cancel_time = int(cancel_dt.timestamp())

                else:
                    if not row['departure_time'].isdigit() or not row['cancel_time'].isdigit():
                        raise IOError('Time must be an integer. \
                                        If you want to use a datetime string, set config.io.parse_dates to True')
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
                raise IOError(f"unable to parse request {request_id} from row due to invalid value(s): {row}")

    @property
    def geoid(self):
        return self.origin

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

        :param geoid: The new request origin
        :return: The updated request
        """
        return self._replace(
            origin=geoid
        )
