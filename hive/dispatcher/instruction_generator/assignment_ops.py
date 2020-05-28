from __future__ import annotations

from typing import TypeVar, Tuple, Callable, NamedTuple
import numpy as np
import functools as ft
from scipy.optimize import linear_sum_assignment

EntityId = str


class Entity:
    id: EntityId


class AssignmentSolution(NamedTuple):
    solution: Tuple[Tuple[EntityId, EntityId], ...] = ()
    solution_cost: float = 0.0

    def add(self, pair: Tuple[EntityId, EntityId], cost: float) -> AssignmentSolution:
        return self._replace(
            solution=(pair, ) + self.solution,
            solution_cost=self.solution_cost + cost
        )


def find_assignment(assignees: Tuple[Entity],
                    targets: Tuple[Entity],
                    cost_fn: Callable[[Entity, Entity], float]) -> AssignmentSolution:
    """

    :param assignees: entities we are assigning to. assumed to have an id field.
    :param targets: the different entities that each assignee can be assigned to. assumed to have an id field.
    :param cost_fn: computes the cost of choosing a specific assignee (slot 1) with a specific target (slot 2)
    :return: a collection of pairs of (AssigneeId, TargetId) indicating the solution, along with it's cost
    """

    initial_cost = float("inf")
    table = np.full((len(assignees), len(targets)), initial_cost)

    for i in range(len(assignees)):
        for j in range(len(targets)):
            table[i][j] = cost_fn(assignees[i], targets[j])

    # apply the Kuhn-Munkres algorithm
    rows, cols = linear_sum_assignment(table)

    # interpret the row/column assignments back to EntityIds and compute the total cost of this assignment
    def _add_to_solution(assignment_solution: AssignmentSolution, i: int) -> AssignmentSolution:
        this_pair = (assignees[rows[i]].id, targets[cols[i]].id)
        this_cost = table[rows[i]][cols[i]]
        return assignment_solution.add(this_pair, this_cost)
    solution = ft.reduce(
        _add_to_solution,
        range(len(assignees)),
        AssignmentSolution()
    )

    return solution
