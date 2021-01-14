from hive.util.typealiases import LinkId
from typing import Optional, Tuple
import re


def create_link_id(src: int, dst: int) -> LinkId:
    """
    creates a LinkId from its source and destination node ids
    :param src: the source node id
    :param dst: the destination node id
    :return: a LinkId
    """
    return f"{src}-{dst}"


def extract_node_ids(link_id: LinkId) -> Tuple[Optional[Exception], Optional[Tuple[int, int]]]:
    """
    expects the provided string is of the form {src_node_id}-{dst_node_id}
    :param link_id: a string that is a LinkId
    :return: an error, or, a tuple containing both node ids
    """
    try:
        regex_result = re.search('(\d+)-(\d+)', link_id)
        if not len(regex_result.groups()) == 2:
            return Exception(f"LinkId {link_id} does not take the form (\d+)-(\d+)"), None
        else:
            src, dst = int(regex_result.group(1)), int(regex_result.group(2))
            return None, (src, dst)
    except Exception as e:
        return e, None


def reverse_link_id(link_id: LinkId) -> Tuple[Optional[Exception], Optional[LinkId]]:
    """
    attempts to reverse a link id by swapping the node ids. can be used to look up the
    "other side of the street" on 2-way streets.
    :param link_id: the link id to reverse
    :return: either an error or the reversed LinkId
    """
    error, node_ids = extract_node_ids(link_id)
    if error:
        return error, None
    else:
        src, dst = node_ids
        result = create_link_id(dst, src)
        return None, result
