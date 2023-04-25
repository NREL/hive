from collections.abc import Sequence
from typing import Union, Optional

HiveTabularDataLists = Optional[Sequence[str]]
HiveTabularDataDicts = Optional[Sequence[dict[str, Union[str, int, float]]]]
