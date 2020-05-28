from __future__ import annotations

import functools as ft
from typing import Tuple, Callable, NamedTuple

import numpy as np
from h3 import h3
from scipy.optimize import linear_sum_assignment

from hive.model.energy import Charger
from hive.model.station import Station
from hive.model.vehicle import Vehicle

EntityId = str


class Entity:
    id: EntityId


class AssignmentSolution(NamedTuple):
    solution: Tuple[Tuple[EntityId, EntityId], ...] = ()
    solution_cost: float = 0.0

    def add(self, pair: Tuple[EntityId, EntityId], cost: float) -> AssignmentSolution:
        return self._replace(
            solution=(pair,) + self.solution,
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

    if len(assignees) == 0 or len(targets) == 0:
        return AssignmentSolution()
    else:
        initial_cost = float("inf")
        table = np.full((len(assignees), len(targets)), initial_cost)

        upper_bound = float("-inf")
        for i in range(len(assignees)):
            for j in range(len(targets)):
                cost = cost_fn(assignees[i], targets[j])
                upper_bound = cost if cost > upper_bound and cost != float("inf") else upper_bound
                table[i][j] = cost

        # linear_sum_assignment borks with infinite values; replace
        # float("inf") with the upper-bound value
        upper_bound += 1
        for i in range(len(assignees)):
            for j in range(len(targets)):
                table[i][j] = upper_bound if table[i][j] == float("inf") else table[i][j]

        # apply the Kuhn-Munkres algorithm
        rows, cols = linear_sum_assignment(table)

        # interpret the row/column assignments back to EntityIds and compute the total cost of this assignment
        def _add_to_solution(assignment_solution: AssignmentSolution, i: int) -> AssignmentSolution:
            this_pair = (assignees[rows[i]].id, targets[cols[i]].id)
            this_cost = table[rows[i]][cols[i]]
            return assignment_solution.add(this_pair, this_cost)

        solution = ft.reduce(
            _add_to_solution,
            range(len(rows)),
            AssignmentSolution()
        )

        return solution


def distance_cost(a: Entity, b: Entity) -> float:
    return h3.h3_distance(a.geoid, b.geoid)


def nearest_shortest_queue(vehicle: Vehicle, station: Station) -> float:
    """
    sort ordering that prioritizes short vehicle queues where possible
    :param vehicle: a vehicle
    :param station: a station
    :return: the distance metric for this station, a function of it's queue size and distance
    """
    dc_chargers = station.total_chargers.get(Charger.DCFC, 0)
    if not dc_chargers:
        return float("inf")
    else:
        # actual_distance = H3Ops.great_circle_distance(veh.geoid, station.geoid)
        distance = h3.h3_distance(vehicle.geoid, station.geoid)
        queue_factor = station.enqueued_vehicle_count_for_charger(Charger.DCFC) / dc_chargers
        distance_metric = distance + distance * queue_factor
        return distance_metric
