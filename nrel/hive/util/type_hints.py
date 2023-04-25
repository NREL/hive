from collections.abc import Iterable
from typing import Union, Optional

HiveTabularDataLists = Optional[Iterable[str]]
HiveTabularDataDicts = Optional[Iterable[dict[str, Union[str, int, float]]]]
