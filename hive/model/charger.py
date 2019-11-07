from __future__ import annotations

from typing import NamedTuple
from hive.util.typealiases import *


class Charger(NamedTuple):
    rate: KwH
