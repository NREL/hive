from __future__ import annotations

from typing import Tuple, NamedTuple, FrozenSet

from hive.util.typealiases import MembershipId

PUBLIC_MEMBERSHIP_ID = "public"


class Membership(NamedTuple):
    """
    class representing a collection of membership ids.
    """

    memberships: FrozenSet[MembershipId] = frozenset()

    @classmethod
    def from_tuple(cls, member_ids: Tuple[MembershipId, ...]) -> Membership:
        """
        build membership from tuple.

        :param member_ids:
        :return:
        """
        if any([m == PUBLIC_MEMBERSHIP_ID for m in member_ids]):
            raise TypeError(f"{PUBLIC_MEMBERSHIP_ID} is reserved, please use another membership id")
        return Membership(frozenset(member_ids))

    @classmethod
    def single_membership(cls, membership_id: MembershipId) -> Membership:
        """
        build membership with single member id

        :param membership_id:
        :return:
        """
        if membership_id == PUBLIC_MEMBERSHIP_ID:
            raise TypeError(f"{PUBLIC_MEMBERSHIP_ID} is reserved, please use another membership id")
        return Membership(frozenset((membership_id,)))

    @property
    def public(self) -> bool:
        return len(self.memberships) == 0

    def add_membership(self, membership_id: MembershipId) -> Membership:
        """
        add a single membership id

        :param membership_id:
        :return:
        """
        if membership_id == PUBLIC_MEMBERSHIP_ID:
            raise TypeError(f"{PUBLIC_MEMBERSHIP_ID} is reserved, please use another membership id")
        new_member_ids = [m for m in self.memberships] + [membership_id]
        return self._replace(memberships=frozenset(new_member_ids))

    def memberships_in_common(self, other_membership: Membership) -> FrozenSet[MembershipId]:
        """
        lists the MembershipIds in common with another Membership, such as to identify
        which ride hail service provider was used to pick up a request

        :param other_membership: the memberships of another entity in the simulation
        :return: the memberships in common
        """
        return self.memberships.intersection(other_membership.memberships)

    def grant_access_to_membership(self, other_membership: Membership) -> bool:
        """
        returns true if another membership has access to this membership

        :param other_membership:
        :return:
        """
        if self.public:
            return True
        else:
            return len(self.memberships_in_common(other_membership)) > 0

    def grant_access_to_membership_id(self, membership_id: MembershipId) -> bool:
        """
        returns true if the membership id is valid for this membership

        :param membership_id:
        :return:
        """
        if self.public:
            return True
        else:
            return membership_id in self.memberships

    def as_tuple(self) -> Tuple[MembershipId, ...]:
        return tuple(m for m in self.memberships)

    def __str__(self):
        """
        string representation of memberships
        :return: a comma-delimited string of the membership ids
        """
        return ",".join(self.memberships)

    def to_json(self):
        if len(self.memberships) > 0:
            return list(self.memberships)
        else:
            return None
