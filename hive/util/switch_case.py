from __future__ import annotations

from abc import abstractmethod, ABC
from typing import Dict

from hive.util.typealiases import *


Key = TypeVar('Key')
"""
the type used to switch off of
"""

Arguments = TypeVar('Arguments')
"""
the type of the arguments fed to the inner switch clause
"""

Result = TypeVar('Result')
"""
the type returned from the SwitchCase (can be "Any")
"""


class SwitchCase(ABC):

    @abstractmethod
    def _default(self, arguments: Arguments) -> Result:
        """
        called when "key" does not exist in the SwitchCase


        :param arguments: the arguments to pass in the default case
        :return:
        """

    case_statement: Dict[Key, Callable[[Arguments], Result]] = {}

    @classmethod
    def switch(cls, case, payload: Arguments) -> Result:
        return cls.case_statement.get(case, cls._default)(cls, payload)
