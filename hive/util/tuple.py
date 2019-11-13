from __future__ import annotations

from typing import Tuple


def head_tail(tup: Tuple):
    if not tup:
        return (), None
    elif len(tup) == 1:
        return tup, None
    else:
        return tup[0], tup[1:]
