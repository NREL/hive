from __future__ import annotations

from abc import abstractmethod, ABC
from dataclasses import dataclass
from typing import Tuple

from nrel.hive.model.entity_position import EntityPosition
from nrel.hive.model.membership import Membership
from nrel.hive.util.typealiases import MembershipId


@dataclass(frozen=True)
class EntityMixin:
    id: str
    position: EntityPosition
    membership: Membership


class EntityABC(ABC):
    """
    Interface for creating a generic entity
    """

    @property
    @abstractmethod
    def geoid(self) -> str:
        """
        returns the geoid of the entity

        :return: the geoid of the entity
        """

    @abstractmethod
    def set_membership(self, member_ids: Tuple[str, ...]) -> EntityABC:
        """
        sets the membership(s) of the entity

        :param member_ids: a Tuple containing updated membership(s) of the entity
        :return: the updated entity
        """

    @abstractmethod
    def add_membership(self, membership_id: MembershipId) -> EntityABC:
        """
        adds a membership to the entity

        :param membership_id: a membership id for the entity
        :return: the updated entity
        """


class Entity(EntityMixin, EntityABC):
    """"""
