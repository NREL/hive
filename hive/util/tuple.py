from __future__ import annotations

from typing import Tuple


def head_tail(tup: Tuple):
    if not tup:
        raise IndexError("called head_tail on empty Tuple")
    elif len(tup) == 1:
        return tup, ()
    else:
        return tup[0], tup[1:]
