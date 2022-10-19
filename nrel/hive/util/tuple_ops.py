import itertools as it
from typing import Tuple, TypeVar, Optional, Callable


class TupleOps:
    T = TypeVar('T')

    @classmethod
    def is_empty(cls, xs: Tuple[T, ...]) -> bool:
        return len(xs) == 0

    @classmethod
    def non_empty(cls, xs: Tuple[T, ...]) -> bool:
        return not TupleOps.is_empty(xs)

    @classmethod
    def remove(cls, xs: Tuple[T, ...], value: T) -> Tuple[T, ...]:
        removed = tuple(filter(lambda x: x != value, xs))
        if len(removed) == len(xs):
            return ()
        else:
            return removed

    @classmethod
    def head(cls, xs: Tuple[T, ...]) -> T:
        if len(xs) == 0:
            raise IndexError("called head on empty Tuple")
        else:
            return xs[0]

    @classmethod
    def head_optional(cls, xs: Tuple[T, ...]) -> Optional[T]:
        if len(xs) == 0:
            return None
        else:
            return xs[0]

    @classmethod
    def last(cls, xs: Tuple[T, ...]) -> T:
        if len(xs) == 0:
            raise IndexError("called last on empty Tuple")
        else:
            return xs[-1]

    @classmethod
    def last_optional(cls, xs: Tuple[T, ...]) -> Optional[T]:
        if len(xs) == 0:
            return None
        else:
            return xs[-1]

    @classmethod
    def head_tail(cls, tup: Tuple[T, ...]) -> Tuple[T, Tuple[T, ...]]:
        if not tup:
            raise IndexError("called head_tail on empty Tuple")
        elif len(tup) == 1:
            return tup[0], ()
        else:
            return tup[0], tup[1:]

    @classmethod
    def tail(cls, tup: Tuple[T, ...]) -> Tuple[T, ...]:
        if not tup:
            return ()
        elif len(tup) == 1:
            return ()
        else:
            remaining = tup[1:]
            return remaining

    @classmethod
    def partition(cls,
                  predicate: Callable[[T], bool],
                  t: Tuple[T, ...]) -> Tuple[Tuple[T, ...], Tuple[T, ...]]:
        """
        partitions a tuple into two tuples where members of the first tuple
        match the case where the provided predicate is True

        taken from https://docs.python.org/3/library/itertools.html (but result tuples reversed for readability)

        :param predicate: tests membership in result tuples
        :param t: the source tuple
        :return:
        """
        t1, t2 = it.tee(t)
        return tuple(filter(predicate, t1)), tuple(it.filterfalse(predicate, t2))

    @classmethod
    def flatten(cls, nested_tuple: Tuple[Tuple[T, ...], ...]) -> Tuple[T, ...]:
        """
        flattens a tuple of tuples

        taken from https://stackoverflow.com/a/10636583/11087167

        :param nested_tuple: tuple to flatten
        :return: flattened tuple
        """

        return tuple(sum(nested_tuple, ()))
    
    @classmethod
    def prepend(cls, x: T, xs: Tuple[T, ...]) -> Tuple[T, ...]:
        """
        prepends an element to a tuple
        """
        return (x,) + xs
