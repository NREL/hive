from typing import Optional, Union, NamedTuple

from h3 import h3

from hive.model.roadnetwork.link import Link
from hive.model.roadnetwork.property_link import PropertyLink
from hive.model.roadnetwork.roadnetwork import RoadNetwork
from hive.util.typealiases import Time


class LinkTraversal(NamedTuple):
    """
    represents the traversal of a link.
    traversed_link represents any part of the link that was traversed.
    remaining_link represents any part of the link that remains to be traversed
    remaining_time represents any time the agent has left to traverse additional links
    """
    traversed: Optional[PropertyLink]
    remaining: Optional[PropertyLink]
    remaining_time: Time


def traverse_up_to(road_network: RoadNetwork,
                   property_link: PropertyLink,
                   available_time: Time) -> Union[Exception, LinkTraversal]:
    """
    using the ground truth road network, and some agent Link traversal, attempt to traverse
    the link, based on travel time calculations from the Link's PropertyLink attributes.
    :param road_network: the road network
    :param property_link: the plan the agent has to traverse a subset of a road network link
    :param available_time: the remaining time the agent has in this time step
    :return: the updated traversal, or, an exception.
             on update, if there is any remaining traversal, return an updated Link.
             if no traversal remains, return None.
             regardless, return the agent's remaining time after traversing
             if there was any error, return the exception instead.
    """
    property_link = road_network.get_link(property_link.link_id)
    if property_link is None:
        return AttributeError(f"attempting to traverse link {property_link.link_id} which does not exist")
    elif property_link.start == property_link.end:
        # already done!
        return LinkTraversal(
            traversed=None,
            remaining=None,
            remaining_time=available_time
        )
    else:
        # traverse up to available_time across this link
        current_link_speed = property_link.speed
        agent_link_hex_dist = h3.h3_distance(property_link.start, property_link.end)
        agent_link_dist = road_network.neighboring_hex_distance * agent_link_hex_dist
        agent_link_travel_time = agent_link_dist / current_link_speed

        if agent_link_travel_time <= available_time:
            # we can complete this link, so we return (remaining) Link = None
            return LinkTraversal(
                traversed=property_link,
                remaining=None,
                remaining_time=available_time - agent_link_travel_time
            )
        else:
            # we do not have enough time to finish traversing this link, so, just traverse part of it,
            # leaving no remaining time.

            # find how many hexes we can traverse
            agent_hex_dist_lim = int((available_time * current_link_speed) / road_network.neighboring_hex_distance)
            this_link_hexes = h3.h3_line(property_link.link.start, property_link.link.end)

            # update our agent's link to only include the remaining hexes to traverse
            # find the hexes,
            # split as this and next hexes, and then
            # re-cast as Links
            this_hexes = this_link_hexes[0:agent_hex_dist_lim+1]
            this_traversal_o, this_traversal_d = this_hexes[0], this_hexes[-1]
            this_traversal = Link(property_link.link_id, this_traversal_o, this_traversal_d)

            next_hexes = this_link_hexes[agent_hex_dist_lim:]
            next_traversal_o, next_traversal_d = next_hexes[0], next_hexes[-1]
            next_traversal = Link(property_link.link_id, next_traversal_o, next_traversal_d)
            return LinkTraversal(
                traversed=property_link.update_link(this_traversal, road_network.neighboring_hex_distance),
                remaining=property_link.update_link(next_traversal, road_network.neighboring_hex_distance),
                remaining_time=0
            )

