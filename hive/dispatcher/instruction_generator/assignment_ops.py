from __future__ import annotations

import functools as ft
from typing import Tuple, Callable, NamedTuple

import numpy as np
from h3 import h3
from scipy.optimize import linear_sum_assignment

from hive.model.energy import Charger
from hive.model.station import Station
from hive.model.vehicle import Vehicle
from hive.util import H3Ops, GeoId

EntityId = str


class Entity:
    """
    this class is used as a type hint (duck-typing style) for the following functions
    but is not intended to be implemented.
    """
    id: EntityId
    geoid: GeoId


class AssignmentSolution(NamedTuple):
    """
    each call of find_assignment produces an AssignmentSolution which has any
    assignments (a pair of two ids), along with the total cost of this assignment.
    """
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

        # evaluate the cost of all possible assignments between each assignee/target pair
        upper_bound = float("-inf")
        for i in range(len(assignees)):
            for j in range(len(targets)):
                cost = cost_fn(assignees[i], targets[j])
                upper_bound = cost if cost > upper_bound and cost != float("inf") else upper_bound
                table[i][j] = cost

        # linear_sum_assignment borks with infinite values; this 2nd step replaces
        # float("inf") values with an upper-bound value which is 1 beyond our highest-observed value
        upper_bound += 1
        table[table == float("inf")] = upper_bound

        # apply the Kuhn-Munkres algorithm
        rows, cols = linear_sum_assignment(table)

        # interpret the row/column assignments back to EntityIds and compute the total cost of this assignment
        def _add_to_solution(assignment_solution: AssignmentSolution, i: int) -> AssignmentSolution:
            this_pair = (assignees[rows[i]].id, targets[cols[i]].id)
            this_cost = table[rows[i]][cols[i]]
            return assignment_solution.add(this_pair, this_cost)

        solution = ft.reduce(_add_to_solution, range(len(rows)), AssignmentSolution())

        return solution


def h3_distance_cost(a: Entity, b: Entity) -> float:
    """
    cost function based on the h3_distance between two entities
    :param a: one entity, expected to have a geoid
    :param b: another entity, expected to have a geoid
    :return: the h3_distance (number of cells between)
    """
    distance = h3.h3_distance(a.geoid, b.geoid)
    return distance


def great_circle_distance_cost(a: Entity, b: Entity) -> float:
    """
    cost function based on the great circle distance between two entities.
    reverts h3 geoid to a lat/lon pair and calculates the haversine distance.

    :param a: one entity, expected to have a geoid
    :param b: another entity, expected to have a geoid
    :return: the haversine (great circle) distance in lat/lon
    """
    distance = H3Ops.great_circle_distance(a.geoid, b.geoid)
    return distance


def nearest_shortest_queue(vehicle: Vehicle, station: Station) -> float:
    """
    sort ordering that prioritizes short vehicle queues where possible, using h3_distance
    as the base distance metric and extending that value by the proportion of available chargers

    :param vehicle: a vehicle
    :param station: a station
    :return: the distance metric for this station, a function of it's queue size and distance
    """
    dc_chargers = station.total_chargers.get("DCFC", 0)
    if not dc_chargers:
        return float("inf")
    else:
        distance = h3.h3_distance(vehicle.geoid, station.geoid)
        queue_factor = station.enqueued_vehicle_count_for_charger("DCFC") / dc_chargers
        distance_metric = distance + distance * queue_factor
        return distance_metric
