from __future__ import annotations

from typing import NamedTuple, Union

from hive.util.typealiases import LinkId, GeoId
from hive.model.roadnetwork.link import Link, link_distance_km
from hive.util.units import Kilometers, Kmph, Seconds, hours_to_seconds


class PropertyLink(NamedTuple):
    """
    a link on the road network which also has road network attributes such as
    distance, speed, and travel time

    :param link_id: The id of the underlying link in the network.
    :type link_id: :py:obj:`LinkId`
    :param link: The underlying link in the network.
    :type link: :py:obj:`Link`
    :param distance: distance of the property link
    :type distance_km: :py:obj:`kilometers`
    :param speed: speed of the property link
    :type speed_kmph: :py:obj:`kilometers/hour`
    :param travel_time: (estimated) travel time of the property link
    :type travel_time_hours: :py:obj:`hours`
    """
    link_id: LinkId
    link: Link
    distance_km: Kilometers
    speed_kmph: Kmph
    travel_time_seconds: Seconds

    # grade: float # nice in the future?'

    @classmethod
    def build(cls, link: Link, speed_kmph: Kmph) -> PropertyLink:
        """
        alternative constructor which sets distance/travel time based on underlying h3 grid

        :param link: the underlying link representation
        :param speed_kmph: the speed for traversing the link
        :return: a PropertyLink build around this Link
        """
        dist_km = link_distance_km(link)
        tt_hours = dist_km / speed_kmph
        tt_seconds = hours_to_seconds(tt_hours)
        return PropertyLink(
            link_id=link.link_id,
            link=link,
            distance_km=dist_km,
            speed_kmph=speed_kmph,
            travel_time_seconds=tt_seconds,
        )

    @property
    def start(self) -> GeoId:
        return self.link.start

    @property
    def end(self) -> GeoId:
        return self.link.end

    def update_speed(self, speed_kmph: Kmph) -> PropertyLink:
        """
        Update the speed of the property link

        :param speed_kmph: speed to update to
        :return: an updated PropertyLink
        """
        return self._replace(speed_kmph=speed_kmph)

    def update_link(self, updated_link: Link) -> Union[AttributeError, PropertyLink]:
        """
        some operations call for updating the the underlying link representation but
        maintaining the properties of the link which are not tied to the link representation.

        :param updated_link: the new Link data
        :return: the updated PropertyLink
        """
        # todo: is it ok to re-calculate distance/travel time here based on h3 distances?
        if self.link_id is not updated_link.link_id:
            return AttributeError(
                f"mismatch: attempting to update PropertyLink {self.link_id} with Link {updated_link.link_id}")
        else:
            dist_km = link_distance_km(updated_link)
            tt_hours = dist_km / self.speed_kmph
            tt_seconds = hours_to_seconds(tt_hours)
            return self._replace(
                link=updated_link,
                distance_km=dist_km,
                travel_time_seconds=tt_seconds,
            )

