from abc import ABCMeta
from typing import NamedTupleMeta


class ABCNamedTupleMeta(ABCMeta, NamedTupleMeta):
    """
    this class allows an abstract base class to be inherited as a behavior attached
    to a NamedTuple. see https://stackoverflow.com/questions/51860186/namedtuple-class-with-abc-mixin

    example:
    class MyBehavior(metaclass=ABCNamedTupleMeta):
        @abstractmethod
        def do_something(self, it: Iterable[str]) -> str:
            pass

    class MyNamedTuple(NamedTuple, MyBehavior):
        attr1: str
        def do_something(self, it):
            return self.attr1 + it
    """
