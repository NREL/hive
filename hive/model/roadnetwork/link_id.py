from hive.util.typealiases import LinkId
from typing import Optional, Tuple, TypeVar
from ast import literal_eval
import re

NodeId = TypeVar('NodeId')

def create_link_id(src: int, dst: int) -> LinkId:
    """
    creates a LinkId from its source and destination node ids
    :param src: the source node id
    :param dst: the destination node id
    :return: a LinkId
    """
    return f"{src}-{dst}"


def extract_node_ids(link_id: LinkId) -> Tuple[Optional[Exception], Optional[Tuple[NodeId, NodeId]]]:
    """
    expects the provided string is of the form {src_node_id}-{dst_node_id}
    :param link_id: a string that is a LinkId
    :return: an error, or, a tuple containing both node ids
    """
    result = link_id.split("-")
    if len(result) < 2:
        return Exception(f"LinkId {link_id} does not take the form src_node_id-dst_node_id"), None
    elif len(result) > 2:
        return Exception(f"LinkId {link_id} can only have one dash (-) character in the form src_node_id-dst_node_id"), None
    else:
        try:
            src = literal_eval(result[0])
            dst = literal_eval(result[1])
        except ValueError:
            return Exception(f"LinkId {link_id} cannot be parsed."), None

        return None, (src, dst)


def reverse_link_id(link_id: LinkId) -> Tuple[Optional[Exception], Optional[LinkId]]:
    """
    attempts to reverse a link id by swapping the node ids. can be used to look up the
    "other side of the street" on 2-way streets.
    :param link_id: the link id to reverse
    :return: either an error or the reversed LinkId
    """
    error, node_ids = extract_node_ids(link_id)
    if error:
        response = Exception(f"failure during link reversal for link {link_id}")
        response.__cause__ = error
        return response, None
    else:
        src, dst = node_ids
        result = create_link_id(dst, src)
        return None, result
