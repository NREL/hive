from typing import Any, Callable, Iterable
from returns.io import IOResult
from returns.result import ResultE, Success, Failure
from returns.unsafe import unsafe_perform_io

import functools as ft


def throw_on_failure(io_result: IOResult):
    """
    helper that throws an io result if it contains a Failure

    should only be used in the hive.app module (at the "end-of-the-world").


    :param io_result: a result from some IO operation
    :raises: any error result
    """
    inner_result = unsafe_perform_io(io_result)
    if isinstance(inner_result._inner_value, Exception):
        raise inner_result._inner_value


Accumulator = Any
Item = Any


def apply_op_to_accumulator(
    op: Callable[[Item], Callable[[Accumulator], ResultE[Accumulator]]],
    sequence: Iterable[Item],
    initial: Accumulator,
) -> ResultE[Accumulator]:
    """
    helper to apply an operation to a sequence safely

    :param op: the operation to apply
    :param sequence: the sequence to apply the operation to
    :param initial: the initial value of the accumulator
    """

    def _op(acc, i):
        return acc.bind(op(i))

    return ft.reduce(_op, sequence, Success(initial))
