from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Optional, Dict, TYPE_CHECKING

import h3

from nrel.hive.model.entity import Entity
from nrel.hive.model.entity_position import EntityPosition
from nrel.hive.model.membership import Membership
from nrel.hive.model.passenger import Passenger, create_passenger_id
from nrel.hive.model.roadnetwork.roadnetwork import RoadNetwork
from nrel.hive.model.sim_time import SimTime
from nrel.hive.util.exception import TimeParseError
from nrel.hive.util.units import Currency, KM_TO_MILE

if TYPE_CHECKING:
    from nrel.hive.model.request import RequestRateStructure
    from nrel.hive.runner.environment import Environment
    from nrel.hive.util.typealiases import *


@dataclass(frozen=True)
class Request(Entity):
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
    position: EntityPosition
    membership: Membership

    destination_position: EntityPosition
    departure_time: SimTime
    passengers: Tuple[Passenger, ...]
    allows_pooling: bool
    value: Currency = 0
    dispatched_vehicle: Optional[VehicleId] = None
    dispatched_vehicle_time: Optional[SimTime] = None

    @property
    def geoid(self):
        return self.position.geoid

    @property
    def origin(self):
        return self.position.geoid

    @property
    def destination(self):
        return self.destination_position.geoid

    @classmethod
    def build(
        cls,
        request_id: RequestId,
        origin: GeoId,
        destination: GeoId,
        road_network: RoadNetwork,
        departure_time: SimTime,
        passengers: int,
        allows_pooling: bool,
        fleet_id: Optional[MembershipId] = None,
        value: Currency = 0,
    ) -> Request:
        assert departure_time >= 0
        assert passengers > 0
        origin_position = road_network.position_from_geoid(origin)
        if origin_position is None:
            raise ValueError(
                f"request {request_id} origin cannot be positioned on the road network"
            )
        destination_position = road_network.position_from_geoid(destination)
        if destination_position is None:
            raise ValueError(
                f"request {request_id} destination cannot be positioned on the road network"
            )
        if fleet_id:
            membership = Membership.single_membership(fleet_id)
        else:
            membership = Membership()

        request_as_passengers = [
            Passenger(
                id=create_passenger_id(request_id, pass_idx),
                origin=origin_position.geoid,
                destination=destination_position.geoid,
                departure_time=departure_time,
                membership=membership,
            )
            for pass_idx in range(0, passengers)
        ]

        request = Request(
            id=request_id,
            position=origin_position,
            destination_position=destination_position,
            departure_time=departure_time,
            passengers=tuple(request_as_passengers),
            allows_pooling=allows_pooling,
            membership=membership,
            value=value,
        )
        return request

    @classmethod
    def from_row(
        cls, row: Dict[str, str], env: Environment, road_network: RoadNetwork
    ) -> Tuple[Optional[Exception], Optional[Request]]:
        """
        takes a csv row and turns it into a Request


        :param row: a row as interpreted by csv.DictReader

        :param env: the static environment variables

        :param road_network: the road network
        :return: a Request, or an error
        """
        if "request_id" not in row:
            return (
                IOError("cannot load a request without a 'request_id'"),
                None,
            )
        elif "o_lat" not in row:
            return (
                IOError("cannot load a request without an 'o_lat' value"),
                None,
            )
        elif "o_lon" not in row:
            return (
                IOError("cannot load a request without an 'o_lon' value"),
                None,
            )
        elif "d_lat" not in row:
            return (
                IOError("cannot load a request without a 'd_lat' value"),
                None,
            )
        elif "d_lon" not in row:
            return (
                IOError("cannot load a request without a 'd_lon' value"),
                None,
            )
        elif "departure_time" not in row:
            return (
                IOError("cannot load a request without a 'departure_time'"),
                None,
            )
        elif "passengers" not in row:
            return (
                IOError("cannot load a request without a number of 'passengers'"),
                None,
            )
        else:
            request_id = row["request_id"]
            fleet_id = row.get("fleet_id")
            try:
                o_lat, o_lon = float(row["o_lat"]), float(row["o_lon"])
                d_lat, d_lon = float(row["d_lat"]), float(row["d_lon"])
                o_geoid = h3.geo_to_h3(o_lat, o_lon, env.config.sim.sim_h3_resolution)
                d_geoid = h3.geo_to_h3(d_lat, d_lon, env.config.sim.sim_h3_resolution)

                try:
                    departure_time_result = SimTime.build(row["departure_time"])
                except TimeParseError as e:
                    return e, None

                passengers = int(row["passengers"])
                allows_pooling = (
                    bool(row["allows_pooling"]) if row.get("allows_pooling") is not None else False
                )

                request = Request.build(
                    request_id=request_id,
                    fleet_id=fleet_id,
                    origin=o_geoid,
                    destination=d_geoid,
                    road_network=road_network,
                    departure_time=departure_time_result,
                    passengers=passengers,
                    allows_pooling=allows_pooling,
                )
                return None, request
            except ValueError:
                return (
                    IOError(
                        f"unable to parse request {request_id} from row due to invalid value(s): {row}"
                    ),
                    None,
                )

    def assign_dispatched_vehicle(self, vehicle_id: VehicleId, current_time: SimTime) -> Request:
        """
        allows the dispatcher to update the request that a vehicle has been dispatched to them.
        this does not signal that the vehicle is guaranteed to pick them up.


        :param vehicle_id: the vehicle that is planning to service the request

        :param current_time: the current simulation time
        :return: the updated Request
        """
        return replace(self, dispatched_vehicle=vehicle_id, dispatched_vehicle_time=current_time)

    def unassign_dispatched_vehicle(self) -> Request:
        """
        removes any vehicle listed as assigned to this request
        :return: the updated request
        """
        updated = replace(self, dispatched_vehicle=None, dispatched_vehicle_time=None)
        return updated

    def assign_value(
        self, rate_structure: RequestRateStructure, road_network: RoadNetwork
    ) -> Request:
        """
        used to assign a value to this request based on it's properties as well as possible surge pricing.


        :param rate_structure: the rate structure to apply to the request value
        :param road_network: the road network used for computing distances

        :return: the updated request
        """
        if rate_structure.price_per_mile > 0:
            distance_km = road_network.distance_by_geoid_km(self.origin, self.destination)
            distance_miles = distance_km * KM_TO_MILE
            distance_price = rate_structure.price_per_mile * distance_miles
        else:
            distance_price = 0
        price = rate_structure.base_price + distance_price
        return replace(self, value=max(rate_structure.minimum_price, price))

    def set_membership(self, member_ids: Tuple[str, ...]) -> Request:
        """
        sets the membership(s) of the request

        :param member_ids: a Tuple containing updated membership(s) of therequest
        :return:
        """
        return replace(self, membership=Membership.from_tuple(member_ids))

    def add_membership(self, membership_id: MembershipId) -> Request:
        """
        adds the membership to the request

        :param membership_id: a membership for the request
        :return:
        """
        updated_membership = self.membership.add_membership(membership_id)
        return replace(self, membership=updated_membership)
