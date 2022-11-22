from typing import NamedTuple

from nrel.hive.util.typealiases import LinkId, GeoId


class EntityPosition(NamedTuple):
    """
    A pairing of a geoid at the simulation resolution and a link id which yields the position of an entity
    with the context of a link for directionality.
    """

    link_id: LinkId
    geoid: GeoId
