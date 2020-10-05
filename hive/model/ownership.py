from __future__ import annotations

from enum import Enum
from typing import NamedTuple, FrozenSet, Tuple

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
    members: FrozenSet[VehicleId] = frozenset()

    def is_member(self, vehicle_id: VehicleId) -> bool:
        if self.ownership_type == OwnershipType.PUBLIC:
            return True

        return vehicle_id in self.members

    def add_members(self, vehicle_ids: Tuple[VehicleId, ...]) -> Ownership:
        return self._replace(members=self.members.union(frozenset(vehicle_ids)))

    def remove_members(self, vehicle_ids: Tuple[VehicleId, ...]) -> Ownership:
        return self._replace(members=self.members.difference(frozenset(vehicle_ids)))
