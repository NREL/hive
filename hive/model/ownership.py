from __future__ import annotations

from enum import Enum
from typing import NamedTuple, Tuple, Optional

from hive.util.helpers import TupleOps
from hive.util.typealiases import VehicleId


class OwnershipType(Enum):
    """
    a set of ownership types
    """

    PRIVATE = 0
    PUBLIC = 1

    @classmethod
    def from_string(cls, s: str) -> OwnershipType:
        values = {
            'private': cls.PRIVATE,
            'public': cls.PUBLIC,
        }
        try:
            return values[s]
        except KeyError:
            raise TypeError(f"ownership {s} not recognized, try: private, fleet_private, or public")


class Ownership(NamedTuple):
    """
    class representing the ownership of an entitiy
    """

    ownership_type: OwnershipType
    members: Tuple[Optional[VehicleId], ...] = ()

    def is_member(self, vehicle_id: VehicleId) -> bool:
        if self.ownership_type == OwnershipType.PUBLIC:
            return True

        return vehicle_id in self.members

    def add_member(self, vehicle_id: VehicleId) -> Ownership:
        if self.is_member(vehicle_id):
            return self
        else:
            new_members = self.members + (vehicle_id,)
            return self._replace(members=new_members)

    def remove_member(self, vehicle_id: VehicleId) -> Ownership:
        if not self.is_member(vehicle_id):
            return self
        else:
            new_members = TupleOps.remove(self.members, vehicle_id)
            return self._replace(members=new_members)
