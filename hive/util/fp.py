from returns.io import IOResult
from returns.unsafe import unsafe_perform_io


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