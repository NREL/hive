from typing import Tuple, Optional, TypeVar


class TupleOps:
    T = TypeVar('T')

    @classmethod
    def remove(cls, xs: Tuple[T, ...], value: T) -> Optional[Tuple[T, ...]]:
        removed = tuple(filter(lambda x: x != value, xs))
        if len(removed) == len(xs):
            return None
        else:
            return removed
