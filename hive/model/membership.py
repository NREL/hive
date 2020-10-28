from __future__ import annotations

from typing import Tuple, NamedTuple, FrozenSet

from hive.util.typealiases import MembershipId

DEFAULT_MEMBERSHIP = "default_membership"


class Membership(NamedTuple):
    """
    class representing a collection of membership ids.
    """

    memberships: FrozenSet[MembershipId] = frozenset([DEFAULT_MEMBERSHIP])

    @classmethod
    def from_tuple(cls, member_ids: Tuple[MembershipId, ...]) -> Membership:
        if DEFAULT_MEMBERSHIP in member_ids:
            raise TypeError(f"membership id {DEFAULT_MEMBERSHIP} is a reserved id, please select another")

        return Membership(frozenset(member_ids))

    @classmethod
    def single_membership(cls, member_id: MembershipId) -> Membership:
        if DEFAULT_MEMBERSHIP == member_id:
            raise TypeError(f"membership id {DEFAULT_MEMBERSHIP} is a reserved id, please select another")

        return Membership(frozenset((member_id,)))

    def memberships_in_common(self, other_membership: Membership) -> FrozenSet[MembershipId]:
        """
        lists the MembershipIds in common with another Membership, such as to identify
        which ride hail service provider was used to pick up a request

        :param other_membership: the memberships of another entity in the simulation
        :return: the memberships in common
        """
        return self.memberships.intersection(other_membership.memberships)

    def valid_membership(self, other_membership: Membership) -> bool:
        """
        tests membership against another membership.


        :param other_membership:
        :return: true if there exists at least one overlapping membership id, false otherwise
        """
        return len(self.memberships_in_common(other_membership)) > 0

    def is_member(self, membership_id: MembershipId) -> bool:
        """
        tests if membership id exists in membership set


        :param membership_id:
        :return:
        """
        return membership_id in self.memberships

    def as_tuple(self) -> Tuple[MembershipId, ...]:
        return tuple(m for m in self.memberships)
