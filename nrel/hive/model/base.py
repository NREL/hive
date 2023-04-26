from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Optional, Dict, Tuple, TYPE_CHECKING

import h3

from nrel.hive.model.entity import Entity
from nrel.hive.model.entity_position import EntityPosition
from nrel.hive.model.membership import Membership
from nrel.hive.model.roadnetwork.roadnetwork import RoadNetwork
from nrel.hive.util.exception import SimulationStateError

if TYPE_CHECKING:
    from nrel.hive.util.typealiases import BaseId, GeoId, MembershipId, StationId


@dataclass(frozen=True)
class Base(Entity):
    """
    Represents a base within the simulation.


    :param id: unique base id.
    :type id: str

    :param geoid: location of base.
    :type geoid: GeoId

    :param total_stalls: total number of parking stalls.
    :type total_stalls: int

    :param available_stalls: number of available parking stalls.
    :type available_stalls: int

    :param station_id: Optional station that is located at the base.
    :type station_id: Optional[StationId]
    """

    id: BaseId
    position: EntityPosition
    membership: Membership

    total_stalls: int
    available_stalls: int
    station_id: Optional[StationId]

    @property
    def geoid(self):
        return self.position.geoid

    @classmethod
    def build(
        cls,
        id: BaseId,
        geoid: GeoId,
        road_network: RoadNetwork,
        station_id: Optional[StationId],
        stall_count: int,
        membership: Membership = Membership(),
    ):
        position = road_network.position_from_geoid(geoid)
        if position is None:
            raise ValueError("cannot position base on road network")

        return Base(
            id=id,
            position=position,
            membership=membership,
            total_stalls=stall_count,
            available_stalls=stall_count,
            station_id=station_id,
        )

    @classmethod
    def from_row(
        cls,
        row: Dict[str, str],
        road_network: RoadNetwork,
    ) -> Base:
        """
        converts a csv row to a base

        :param row:
        :param road_network:
        :return:
        """
        if "base_id" not in row:
            raise IOError("cannot load a base without a 'base_id'")
        elif "lat" not in row:
            raise IOError("cannot load a base without an 'lat' value")
        elif "lon" not in row:
            raise IOError("cannot load a base without an 'lon' value")
        elif "stall_count" not in row:
            raise IOError("cannot load a base without a 'stall_count' value")
        else:
            base_id = row["base_id"]
            try:
                lat, lon = float(row["lat"]), float(row["lon"])
                geoid = h3.geo_to_h3(lat, lon, road_network.sim_h3_resolution)
                stall_count = int(row["stall_count"])

                # allow user to leave station_id blank or use the word "none" to signify
                # no station at base
                station_id_name = row["station_id"] if len(row["station_id"]) > 0 else "none"
                station_id = None if station_id_name.lower() == "none" else station_id_name

                # TODO: think about how to assign vehicles to bases based on fleet membership

                return Base.build(
                    id=base_id,
                    geoid=geoid,
                    road_network=road_network,
                    station_id=station_id,
                    stall_count=stall_count,
                )

            except ValueError as e:
                raise IOError(
                    f"unable to parse id {base_id} from row due to invalid value(s): {row}"
                ) from e

    def has_available_stall(self, membership: Membership) -> bool:
        """
        Does base have a stall or not.

        :return: Boolean
        """
        return bool(self.available_stalls > 0) and self.membership.grant_access_to_membership(
            membership
        )

    def checkout_stall(self) -> Optional[Base]:
        """
        Checks out a stall and returns the updated base if there are enough stalls.

        :return: Updated Base or None
        """
        stalls = self.available_stalls
        if stalls < 1:
            return None
        else:
            return replace(self, available_stalls=stalls - 1)

    def return_stall(self) -> Tuple[Optional[Exception], Optional[Base]]:
        """
        Checks out a stall and returns the updated base.

        :return: Updated Base
        """
        stalls = self.available_stalls
        if (stalls + 1) > self.total_stalls:
            return (
                SimulationStateError(
                    f"base {self.id} already has max ({self.total_stalls}) stalls"
                ),
                None,
            )
        else:
            return None, replace(self, available_stalls=stalls + 1)

    def set_membership(self, member_ids: Tuple[str, ...]) -> Base:
        """
        sets the membership(s) of the base

        :param member_ids: a Tuple containing updated membership(s) of the base
        :return:
        """
        return replace(self, membership=Membership.from_tuple(member_ids))

    def add_membership(self, membership_id: MembershipId) -> Base:
        """
        adds the membership to the base

        :param membership_id: a membership for the base
        :return: updated base
        """
        updated_membership = self.membership.add_membership(membership_id)
        return replace(self, membership=updated_membership)
