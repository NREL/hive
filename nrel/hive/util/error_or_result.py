from typing import TypeVar, Tuple, Optional

T = TypeVar("T")

ErrorOr = Tuple[Optional[Exception], Optional[T]]
