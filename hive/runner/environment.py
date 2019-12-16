from typing import NamedTuple

from hive.config import HiveConfig


class Environment(NamedTuple):
    config: HiveConfig
    # powertrains, powercurves here?
