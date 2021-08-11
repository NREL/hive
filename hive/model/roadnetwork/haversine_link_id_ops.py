from typing import Tuple

from hive.util import GeoId, LinkId


def geoids_to_link_id(origin: GeoId, destination: GeoId) -> LinkId:
    """
    constructs a LinkId for HaversineRoadNetworks from two GeoIds
    :param origin: the origin GeoId
    :param destination: the destination GeoId
    :return: a HaversineRoadNetwork LinkId
    """
    link_id = origin + "-" + destination
    return link_id


def link_id_to_geodis(link_id: LinkId) -> Tuple[GeoId, GeoId]:
    """
    unpacks the GeoIds encoded in a HaversineRoadNetwork LinkId
    :param link_id: the LinkId to extract
    :return: the origin and destination GeoIds encoded in this LinkId
    :raises: TypeError, when the provided LinkId does not take the expected form
    """
    ids = link_id.split("-")
    if len(ids) != 2:
        raise (TypeError("LinkId not in expected format of [GeoId]-[GeoId]"))
    start = ids[0]
    end = ids[1]

    return start, end