from __future__ import annotations

from datetime import datetime


class SimTime(int):
    def __new__(cls, value, *args, **kwargs):
        return super(cls, cls).__new__(cls, value)

    def __add__(self, other):
        res = super(SimTime, self).__add__(other)
        return self.__class__(res)

    def __sub__(self, other):
        res = super(SimTime, self).__sub__(other)
        return self.__class__(res)

    def __mul__(self, other):
        res = super(SimTime, self).__mul__(other)
        return self.__class__(res)

    def __repr__(self):
        return datetime.fromtimestamp(self).isoformat()

    def __str__(self):
        return datetime.fromtimestamp(self).isoformat()
