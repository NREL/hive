from __future__ import annotations

from typing import NamedTuple, Optional, Dict, TYPE_CHECKING

import h3

from hive.model.membership import Membership
from hive.model.passenger import Passenger, create_passenger_id
from hive.model.roadnetwork.link import Link
from hive.model.roadnetwork.roadnetwork import RoadNetwork
from hive.model.sim_time import SimTime
from hive.util.exception import TimeParseError
from hive.util.typealiases import *
from hive.util.units import Currency, KM_TO_MILE, Kilometers

if TYPE_CHECKING:
    from hive.model.request import RequestRateStructure
    from hive.runner.environment import Environment


class Request(NamedTuple):
    """
    A ride hail request which is alive in the simulation but not yet serviced.
    It should only exist if the current sim time >= self.departure_time.
    It should be removed once the current sim time >= self.departure_time + config.sim.request_cancel_time_seconds.
    If a vehicle has been dispatched to service this Request, then it should hold the vehicle id
    and the time that vehicle was dispatched to it.

    :param id: A unique id for the request.
    :param origin: The geoid of the request origin.
    :param destination: The geoid of the request destination.
    :param departure_time: The time of departure.
    :param passengers: A tuple of passengers associated with this request.
    :param membership: the membership of the fleet.
    :param dispatched_vehicle: The id of the vehicle dispatched to service this request.
    :param dispatched_vehicle_time: Time time which a vehicle was dispatched for this request.
    """
    id: RequestId
    origin_link: Link
    destination_link: Link
    departure_time: SimTime
    passengers: Tuple[Passenger, ...]
    membership: Membership = Membership()
    value: Currency = 0
    dispatched_vehicle: Optional[VehicleId] = None
    dispatched_vehicle_time: Optional[SimTime] = None

    @property
    def origin(self):
        return self.origin_link.start

    @property
    def destination(self):
        return self.destination_link.end

    @classmethod
    def build(cls,
              request_id: RequestId,
              origin: GeoId,
              destination: GeoId,
              road_network: RoadNetwork,
              departure_time: SimTime,
              passengers: int,
              fleet_id: Optional[MembershipId] = None,
              value: Currency = 0
              ) -> Request:
        assert (departure_time >= 0)
        assert (passengers > 0)
        origin_link = road_network.stationary_location_from_geoid(origin)
        destination_link = road_network.stationary_location_from_geoid(destination)
        request_as_passengers = [
            Passenger(
                create_passenger_id(request_id, pass_idx),
                origin_link.start,
                destination_link.end,
                departure_time
            )
            for pass_idx in range(0, passengers)
        ]
        if fleet_id:
            membership = Membership.single_membership(fleet_id)
        else:
            membership = Membership()

        request = Request(
            id=request_id,
            origin_link=origin_link,
            destination_link=destination_link,
            departure_time=departure_time,
            passengers=tuple(request_as_passengers),
            membership=membership,
            value=value,
        )
        return request

    @property
    def geoid(self):
        return self.origin

    @classmethod
    def from_row(cls, row: Dict[str, str],
                 env: Environment,
                 road_network: RoadNetwork) -> Tuple[Optional[Exception], Optional[Request]]:
        """
        takes a csv row and turns it into a Request


        :param row: a row as interpreted by csv.DictReader

        :param env: the static environment variables

        :param road_network: the road network
        :return: a Request, or an error
        """
        if 'request_id' not in row:
            return IOError("cannot load a request without a 'request_id'"), None
        elif 'o_lat' not in row:
            return IOError("cannot load a request without an 'o_lat' value"), None
        elif 'o_lon' not in row:
            return IOError("cannot load a request without an 'o_lon' value"), None
        elif 'd_lat' not in row:
            return IOError("cannot load a request without a 'd_lat' value"), None
        elif 'd_lon' not in row:
            return IOError("cannot load a request without a 'd_lon' value"), None
        elif 'departure_time' not in row:
            return IOError("cannot load a request without a 'departure_time'"), None
        elif 'passengers' not in row:
            return IOError("cannot load a request without a number of 'passengers'"), None
        else:
            request_id = row['request_id']
            fleet_id = row.get('fleet_id')
            try:

                o_lat, o_lon = float(row['o_lat']), float(row['o_lon'])
                d_lat, d_lon = float(row['d_lat']), float(row['d_lon'])
                o_geoid = h3.geo_to_h3(o_lat, o_lon, env.config.sim.sim_h3_resolution)
                d_geoid = h3.geo_to_h3(d_lat, d_lon, env.config.sim.sim_h3_resolution)

                departure_time_result = SimTime.build(row['departure_time'])
                if isinstance(departure_time_result, TimeParseError):
                    return departure_time_result, None

                passengers = int(row['passengers'])
                request = Request.build(
                    request_id=request_id,
                    fleet_id=fleet_id,
                    origin=o_geoid,
                    destination=d_geoid,
                    road_network=road_network,
                    departure_time=departure_time_result,
                    passengers=passengers
                )
                return None, request
            except ValueError:
                return IOError(f"unable to parse request {request_id} from row due to invalid value(s): {row}"), None

    def assign_dispatched_vehicle(self, vehicle_id: VehicleId, current_time: SimTime) -> Request:
        """
        allows the dispatcher to update the request that a vehicle has been dispatched to them.
        this does not signal that the vehicle is guaranteed to pick them up.


        :param vehicle_id: the vehicle that is planning to service the request

        :param current_time: the current simulation time
        :return: the updated Request
        """
        return self._replace(dispatched_vehicle=vehicle_id, dispatched_vehicle_time=current_time)

    def assign_value(self, rate_structure: RequestRateStructure, distance_km: Kilometers) -> Request:
        """
        used to assign a value to this request based on it's properties as well as possible surge pricing.


        :param rate_structure: the rate structure to apply to the request value
        :return: the updated request
        """
        distance_miles = distance_km * KM_TO_MILE
        price = rate_structure.base_price + (rate_structure.price_per_mile * distance_miles)
        return self._replace(value=max(rate_structure.minimum_price, price))
