from typing import NamedTuple

from hive.config import HiveConfig


class Environment(NamedTuple):
    """
    Environment variables for hive.

    :param config: hive config object.
    :type config: :py:obj:`HiveConfig`
    """
    config: HiveConfig
    # powertrains, powercurves here?
