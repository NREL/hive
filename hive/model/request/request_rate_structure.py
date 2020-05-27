from __future__ import annotations

from typing import NamedTuple, Dict

from hive.util.units import Currency


class RequestRateStructure(NamedTuple):
    """
    A rate structure for a request.
    """
    base_price: Currency = 0
    price_per_mile: Currency = 0
    minimum_price: Currency = 0

    @classmethod
    def from_row(cls, row: Dict[str, str]) -> RequestRateStructure:
        if 'base_price' not in row:
            raise IOError('cannont load rate structure without base_price')
        elif 'price_per_mile' not in row:
            raise IOError('cannont load rate structure without price_per_mile')
        elif 'minimum_price' not in row:
            raise IOError('cannont load rate structure without minimum_price')
        else:
            return RequestRateStructure(
                base_price=float(row['base_price']),
                price_per_mile=float(row['price_per_mile']),
                minimum_price=float(row['minimum_price']),
            )
