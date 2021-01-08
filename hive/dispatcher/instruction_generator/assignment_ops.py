from __future__ import annotations

import functools as ft
from typing import Tuple, Callable, NamedTuple, Dict

import h3
import numpy as np
from scipy.optimize import linear_sum_assignment

from hive.model.roadnetwork.route import route_distance_km, route_travel_time_seconds
from hive.model.station import Station
from hive.model.vehicle.mechatronics.powercurve import powercurve_ops
from hive.model.vehicle.vehicle import Vehicle
from hive.runner import Environment
from hive.state.simulation_state.simulation_state import SimulationState
from hive.state.vehicle_state.charge_queueing import ChargeQueueing
from hive.state.vehicle_state.charging_station import ChargingStation
from hive.util import H3Ops, GeoId, Seconds, Ratio, TupleOps
from hive.util.typealiases import ChargerId

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


def find_assignment(assignees: Tuple[Entity, ...],
                    targets: Tuple[Entity, ...],
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


def nearest_shortest_queue_ranking(vehicle: Vehicle, charger_id: ChargerId):
    """
    set up a shortest queue ranking function which will rank distances from this vehicle
    and look for chargers of this type

    :param vehicle: the vehicle
    :param charger_id: the target charger type
    :return: a station ranking function
    """
    def _inner(station: Station) -> float:
        """
        sort ordering that prioritizes short vehicle queues where possible, using h3_distance
        as the base distance metric and extending that value by the proportion of available chargers


        :param vehicle: a vehicle
        :param station: a station
        :param charger_id: the type of charger we are using
        :return: the distance metric for this station, a function of it's queue size and distance
        """
        dc_chargers = station.total_chargers.get(charger_id, 0)
        if not dc_chargers:
            return float("inf")
        else:
            distance = h3.h3_distance(vehicle.geoid, station.geoid)
            queue_factor = station.enqueued_vehicle_count_for_charger(charger_id) / dc_chargers
            distance_metric = distance + distance * queue_factor
            return distance_metric

    return _inner


def shortest_time_to_charge_ranking(
        vehicle: Vehicle,
        sim: SimulationState,
        env: Environment,
        target_soc: Ratio) -> Tuple[Callable[[Station], Seconds], Dict]:
    """
    ranks this station by an estimate of the time which would pass until this agent reaches a target charge level

    this function returns a distance function which accepts a Station and returns Seconds


    :param vehicle: a vehicle
    :param sim: the simulation state
    :param env: the simulation environment
    :param target_soc: the SoC we are attempting to reach in this charge session
    :return: the distance metric for this vehicle/station pair (lower is better)
    """
    vehicle_mechatronics = env.mechatronics.get(vehicle.mechatronics_id)
    remaining_range = vehicle_mechatronics.range_remaining_km(vehicle) if vehicle_mechatronics else 0.0
    cache = {}

    def _inner(station: Station) -> Seconds:
        """
        given a station charging alternative, determine the time it would take to charge
        using the best charger type available

        :param station: the station to rank
        :return: a ranking (estimated travel + queue + charge time)
        """
        route = sim.road_network.route(vehicle.link, station.link)
        distance_km = route_distance_km(route)

        if not vehicle_mechatronics or remaining_range < distance_km:
            # vehicle does not have remaining range to reach this station
            # return a signal that demotes this Station alternative to the bottom of the ranking
            return 99999999999999
        else:

            def _veh_at_station(v: Vehicle) -> bool:
                return isinstance(v.vehicle_state, ChargingStation) and v.vehicle_state.station_id == station.id

            def _veh_enqueued(v: Vehicle) -> bool:
                return isinstance(v.vehicle_state, ChargeQueueing) and v.vehicle_state.station_id == station.id

            def _time_to_full_by_charger_id(c: ChargerId):
                def _time_to_full(v: Vehicle) -> Seconds:
                    _mech = env.mechatronics.get(v.mechatronics_id)
                    _charger = env.chargers.get(c)
                    if not _mech or not _charger:
                        return 0
                    else:
                        time_est = powercurve_ops.time_to_full(v,
                                                               _mech,
                                                               _charger,
                                                               target_soc,
                                                               sim.sim_timestep_duration_seconds)
                        return time_est

                return _time_to_full

            def _sort_enqueue_time(v: Vehicle) -> float:
                enqueue_time = v.vehicle_state.enqueue_time
                return enqueue_time

            def _greedy_assignment(_charging: Tuple[Seconds, ...],
                                   _enqueued: Tuple[Seconds, ...],
                                   _charger_id: ChargerId,
                                   time_passed: Seconds = 0) -> Seconds:
                """
                computes the time estimated that a slot opens up for this vehicle to begin charging


                :param _charging: a sorted list of remaining charge time estimates
                :param _enqueued: a sorted list of charge time estimates for enqueued vehicles
                :param _charger_id: the id of the charger these vehicles are competing for
                :param time_passed: the amount of time that has been estimated
                :return: the time in the future we should expect to begin charging, determined by a greedy assignment
                """
                if len(_charging) == len(_enqueued) == 0:
                    return time_passed
                elif len(_charging) < station.total_chargers.get(charger_id):
                    return time_passed
                else:
                    # advance time
                    next_released_charger_time = TupleOps.head(_charging)

                    updated_time_passed = time_passed + next_released_charger_time

                    # remove charging agents who are done
                    _charging_time_advanced = map(lambda t: t - next_released_charger_time, _charging)
                    _charging_vacated = tuple(filter(lambda t: t > 0, _charging_time_advanced))

                    vacancies = station.total_chargers.get(_charger_id) - len(_charging_vacated)
                    if vacancies <= 0:
                        # no space for any changes from enqueued -> charging
                        return _greedy_assignment(
                            _charging=_charging_vacated,
                            _enqueued=_enqueued,
                            _charger_id=_charger_id,
                            time_passed=updated_time_passed
                        )
                    else:
                        # dequeue longest-waiting agents
                        _enqueued_to_dequeue = _enqueued[0:vacancies]
                        _updated_enqueued = _enqueued[vacancies:]
                        _updated_charging = tuple(sorted(_charging_vacated + _enqueued_to_dequeue))

                        return _greedy_assignment(
                            _charging=_updated_charging,
                            _enqueued=_updated_enqueued,
                            _charger_id=_charger_id,
                            time_passed=updated_time_passed
                        )

            # collect all vehicles that are either charging or enqueued at this station
            vehicles_at_station = sim.get_vehicles(filter_function=_veh_at_station)
            vehicles_enqueued = sim.get_vehicles(filter_function=_veh_enqueued, sort=True, sort_key=_sort_enqueue_time)

            estimates = {}
            for charger_id in station.total_chargers.keys():
                charger = env.chargers.get(charger_id)
                if not vehicle_mechatronics.valid_charger(charger):
                    # vehicle can't use this charger so we skip it
                    continue

                # compute the charge time for the vehicle we are ranking
                this_vehicle_charge_time = powercurve_ops.time_to_full(vehicle,
                                                                       vehicle_mechatronics,
                                                                       charger,
                                                                       target_soc,
                                                                       sim.sim_timestep_duration_seconds)

                # collect all estimated remaining charge times for charging vehicles and sort them
                charging = filter(lambda v: v.vehicle_state.charger_id == charger_id, vehicles_at_station)
                charging_time_to_full: Tuple[Seconds, ...] = tuple(sorted(map(_time_to_full_by_charger_id(charger_id), charging)))

                # collect estimated remaining charge times for vehicles enqueued for this charger
                # leave them sorted by enqueue time
                enqueued = filter(lambda v: v.vehicle_state.charger_id == charger_id, vehicles_enqueued)
                enqueued_time_to_full: Tuple[Seconds, ...] = tuple(map(_time_to_full_by_charger_id(charger_id), enqueued))

                # compute the estimated wait time to access a charger for the vehicle we are ranking
                wait_estimate_for_charger = _greedy_assignment(charging_time_to_full, enqueued_time_to_full, charger_id)

                # combine wait time with charge time
                overall_time_est = this_vehicle_charge_time + wait_estimate_for_charger
                estimates.update({charger_id: overall_time_est})

            if not estimates:
                # there are no chargers the vehicle can use.
                return 99999999999999

            best_charger_id = min(estimates, key=estimates.get)

            # writes to value stored in outer scope
            cache.update({station.id: best_charger_id})

            # return the best "distance" aka shortest estimated time to finish charging
            best_overall_time = estimates.get(best_charger_id)
            dispatch_time_seconds = route_travel_time_seconds(route)
            return dispatch_time_seconds + best_overall_time
    return _inner, cache
