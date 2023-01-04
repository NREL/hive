from typing import NamedTuple


from nrel.hive.util.typealiases import LinkId, GeoId
from nrel.hive.util.rust import USE_RUST


if USE_RUST:
    from hive_core import EntityPosition
else:

    class EntityPosition(NamedTuple):  # type: ignore
        """
        A pairing of a geoid at the simulation resolution and a link id which yields the position of an entity
        with the context of a link for directionality.
        """

        link_id: LinkId
        geoid: GeoId
