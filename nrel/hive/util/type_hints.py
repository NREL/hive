from collections.abc import Iterable
from typing import Union, Optional

HiveData = Union[str, int, float, None]
HiveDataRow = Iterable[Optional[HiveData]]
HiveTabularData = Iterable[Optional[HiveDataRow]]
HiveTabularDataDicts = Iterable[dict[str, HiveData]]
