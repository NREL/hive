from __future__ import annotations

from enum import Enum
from typing import NamedTuple

from immutables import Map

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
            raise TypeError(f"ownership {s} not recognized, try: private or public")


class Ownership(NamedTuple):
    """
    class representing the ownership of an entitiy
    """

    ownership_type: OwnershipType
    members: Map[VehicleId, int] = Map()

    def is_member(self, vehicle_id: VehicleId) -> bool:
        if self.ownership_type == OwnershipType.PUBLIC:
            return True

        return self.members.get(vehicle_id) is not None

    def add_member(self, vehicle_id: VehicleId) -> Ownership:
        if self.is_member(vehicle_id):
            return self
        else:
            return self._replace(members=self.members.set(vehicle_id, 0))

    def remove_member(self, vehicle_id: VehicleId) -> Ownership:
        if not self.is_member(vehicle_id):
            return self
        else:
            return self._replace(members=self.members.delete(vehicle_id))
