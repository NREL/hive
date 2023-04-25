from collections.abc import Sequence
from typing import Union

HiveTabularDataLists = Sequence[str]
HiveTabularDataDicts = Sequence[dict[str, Union[str, int, float]]]
