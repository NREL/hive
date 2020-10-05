from __future__ import annotations

from typing import NamedTuple, FrozenSet

from hive.util.typealiases import MemberId


class Membership(NamedTuple):
    """
    class representing a collection of member ids.
    """

    members: FrozenSet[MemberId] = frozenset('no_membership')

    def valid_membership(self, other_membership: Membership) -> bool:
        """
        tests membership against another membership.

        :param other_membership:
        :return: true if there exists at least one overlapping member id, false otherwise
        """
        return self.members.intersection(other_membership.members) is not None

    def is_member(self, membership_id: MemberId) -> bool:
        """
        tests if membership id exists in member set

        :param membership_id:
        :return:
        """
        return membership_id in self.members
