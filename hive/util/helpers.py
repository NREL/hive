from typing import Tuple, Optional, TypeVar

T = TypeVar('T')


def pop_tuple(xs: Tuple[T], value: T) -> Optional[T]:
    removed = tuple(filter(lambda x: x != value, xs))
    if len(removed) == len(xs):
        return None
    else:
        return removed
