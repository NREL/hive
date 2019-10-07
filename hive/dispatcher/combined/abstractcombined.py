from abc import ABC
from hive.dispatcher.assignment.abstractassignment import AbstractAssignment
from hive.dispatcher.repositioning.abstractrepositioning import AbstractRepositioning


class AbstractCombined(AbstractAssignment, AbstractRepositioning, ABC):
    """
    a combined dispatch algorithm includes both the capacity to
    assign and reposition agents
    """
    pass
