from typing import Optional, NamedTuple, Tuple

from hive.model.roadnetwork.link import Link
from hive.util.helpers import H3Ops
from hive.util.units import Seconds


class LinkTraversal(NamedTuple):
    """
    represents the traversal of a link.


    :param traversed: represents any part of the link that was traversed.
    :type traversed: :py:obj:`Optional[PropertyLink]`

    :param remaining: represents any part of the link that remains to be traversed
    :type remaining: :py:obj:`Optional[PropertyLink]`

    :param remaining_time: represents any time the agent has left to traverse additional links
    :type remaining_time_seconds: :py:obj:`hours`
    """
    traversed: Optional[Link]
    remaining: Optional[Link]
    remaining_time_seconds: Seconds


def traverse_up_to(link: Link,
                   available_time_seconds: Seconds) -> Tuple[Optional[Exception], Optional[LinkTraversal]]:
    """
    using the ground truth road network, and some agent Link traversal, attempt to traverse
    the link, based on travel time calculations from the Link's PropertyLink attributes.


    :param link: the plan the agent has to traverse a subset of a road network link

    :param available_time_seconds: the remaining time the agent has in this time step
    :return: the updated traversal, or, an exception.
             on update, if there is any remaining traversal, return an updated Link.
             if no traversal remains, return None.
             regardless, return the agent's remaining time after traversing
             if there was any error, return the exception instead.
    """
    if link is None:
        return AttributeError(f"attempting to traverse link {link.link_id} which does not exist"), None
    elif link.start == link.end:
        # already done!
        result = LinkTraversal(
            traversed=None,
            remaining=None,
            remaining_time_seconds=available_time_seconds
        )
        return None, result
    else:
        # traverse up to available_time_hours across this link
        if link.travel_time_seconds <= available_time_seconds:
            # we can complete this link, so we return (remaining) Link = None
            result = LinkTraversal(
                traversed=link,
                remaining=None,
                remaining_time_seconds=(available_time_seconds - link.travel_time_seconds)
            )
            return None, result
        else:
            # we do not have enough time to finish traversing this link, so, just traverse part of it,
            # leaving no remaining time.

            # find the point in this link to split into two sub-links
            mid_geoid = H3Ops.point_along_link(link, available_time_seconds)

            # create two sub-links, one for the part that was traversed, and one for the remaining part
            traversed = Link.build(link.link_id, link.start, mid_geoid, speed_kmph=link.speed_kmph)
            remaining = Link.build(link.link_id, mid_geoid, link.end, speed_kmph=link.speed_kmph)

            result = LinkTraversal(
                traversed=traversed,
                remaining=remaining,
                remaining_time_seconds=0,
            )
            return None, result

