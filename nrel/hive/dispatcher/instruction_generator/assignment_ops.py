from __future__ import annotations

import functools as ft
import logging
from typing import Dict, Tuple, Callable, NamedTuple, Optional, TYPE_CHECKING

import h3
import numpy as np
from scipy.optimize import linear_sum_assignment

from nrel.hive.model.roadnetwork.route import (
    route_distance_km,
    route_travel_time_seconds,
)
from nrel.hive.model.station.station import Station
from nrel.hive.model.vehicle.mechatronics.powercurve import powercurve_ops
from nrel.hive.model.vehicle.vehicle import Vehicle
from nrel.hive.runner import Environment
from nrel.hive.state.simulation_state.simulation_state import SimulationState
from nrel.hive.state.vehicle_state.charge_queueing import ChargeQueueing
from nrel.hive.state.vehicle_state.charging_station import ChargingStation
from nrel.hive.util.h3_ops import H3Ops
from nrel.hive.util.tuple_ops import TupleOps

if TYPE_CHECKING:
    from nrel.hive.util.units import Ratio, Seconds
    from nrel.hive.util.typealiases import *
    from nrel.hive.model.entity import EntityABC


log = logging.getLogger(__name__)

MAX_DIST = 999999999.0


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
            solution_cost=self.solution_cost + cost,
        )


def find_assignment(
    assignees: Tuple[EntityABC, ...],
    targets: Tuple[EntityABC, ...],
    cost_fn: Callable[[EntityABC, EntityABC], float],
) -> AssignmentSolution:
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


def h3_distance_cost(a: EntityABC, b: EntityABC) -> float:
    """
    cost function based on the h3_distance between two entities

    :param a: one entity, expected to have a geoid
    :param b: another entity, expected to have a geoid
    :return: the h3_distance (number of cells between)
    """
    distance = h3.h3_distance(a.geoid, b.geoid)
    return distance


def great_circle_distance_cost(a: EntityABC, b: EntityABC) -> float:
    """
    cost function based on the great circle distance between two entities.
    reverts h3 geoid to a lat/lon pair and calculates the haversine distance.


    :param a: one entity, expected to have a geoid
    :param b: another entity, expected to have a geoid
    :return: the haversine (great circle) distance in lat/lon
    """
    distance = H3Ops.great_circle_distance(a.geoid, b.geoid)
    return distance


def nearest_shortest_queue_distance(
    vehicle: Vehicle, env: Environment
) -> Callable[[Station], float]:
    """
    set up a shortest queue distance function which will rank station alternatives based on
    the availability of on-shift charging and a simple heuristic based on Euclidean distance
    and smallest queue size.

    :param vehicle: the vehicle
    :param env: simulation environment
    :return: a station distance function
    """

    def fn(station: Station) -> float:
        result = nearest_shortest_queue_ranking(vehicle, station, env, MAX_DIST)
        if result is None:
            return MAX_DIST  #
        else:
            _, rank = result
            return rank

    return fn


def nearest_shortest_queue_ranking(
    vehicle: Vehicle, station: Station, env: Environment, max_dist=999999999.0
) -> Tuple[Optional[ChargerId], float]:
    """
    sort ordering that prioritizes short vehicle queues where possible, using h3_distance
    as the base distance metric and extending that value by the proportion of available chargers

    :param vehicle: the vehicle
    :param station: a station
    :param env: simulation environment
    :param max_dist: upper-bound on distance values
    :return: the distance metric for this station, a function of it's queue sizes and h3 distance
    """

    distance = h3.h3_distance(vehicle.geoid, station.geoid)

    def _inner(
        acc: Tuple[Optional[ChargerId], float], charger_id: ChargerId
    ) -> Tuple[Optional[ChargerId], float]:
        vehicle_mechatronics = env.mechatronics.get(vehicle.mechatronics_id)
        if vehicle_mechatronics is None:
            log.error(f"mechatronics {vehicle.mechatronics_id} not found for vehicle {vehicle.id}")
            return (None, 0.0)

        charger = env.chargers.get(charger_id)
        if charger is None:
            log.error(f"charger id {charger_id} not found in environment")
            return (None, 0.0)

        total_chargers = station.get_total_chargers(charger_id)
        if (
            not vehicle_mechatronics.valid_charger(charger)
            or total_chargers is None
            or total_chargers == 0
        ):
            # vehicle can't use this charger so we skip it, or,
            # station doesn't actually have this charger (an error condition really)
            return acc
        else:
            prev_best_charger_id, prev_best_distance_metric = acc
            enqueued_for_charger_id = station.enqueued_vehicle_count_for_charger(charger_id)
            if enqueued_for_charger_id is None:
                log.error(f"charger id {charger_id} not found at station {station.id}")
                enqueued_for_charger_id = 0

            queue_factor = enqueued_for_charger_id / total_chargers
            this_distance_metric = distance + distance * queue_factor
            if prev_best_distance_metric < this_distance_metric:
                return acc
            else:
                return charger_id, this_distance_metric

    # find the lowest nearest_shortest_queue distance metric
    # amongst the possible on-shift charging options at this station
    initial: Tuple[Optional[str], float] = (None, max_dist)
    best_charger_id, best_charger_rank = ft.reduce(
        _inner, station.on_shift_access_chargers, initial
    )

    return (
        None if best_charger_id is None else best_charger_id,
        best_charger_rank,
    )


def shortest_time_to_charge_distance(
    vehicle: Vehicle, sim: SimulationState, env: Environment, target_soc: Ratio
) -> Callable[[Station], float]:
    """
    ranks this station by an estimate of the time which would pass until this agent reaches a target charge level

    this function returns a distance function which accepts a Station and returns Seconds


    :param vehicle: a vehicle
    :param sim: the simulation state
    :param env: the simulation environment
    :param target_soc: the SoC we are attempting to reach in this charge session
    :return: the distance metric for this vehicle/station pair (lower is better)
    """

    def fn(station: Station) -> float:
        result = shortest_time_to_charge_ranking(sim, env, vehicle, station, target_soc)
        dist = 999999999.0 if result is None else result[1]
        return dist

    return fn


def shortest_time_to_charge_ranking(
    sim: SimulationState,
    env: Environment,
    vehicle: Vehicle,
    station: Station,
    target_soc: Ratio,
) -> Optional[Tuple[ChargerId, float]]:
    """
    given a station charging alternative, determine the time it would take to charge
    using the best charger type available

    :param sim: simulation state
    :param env: the simulation environment
    :param vehicle: the vehicle
    :param station: the station to rank
    :param target_soc: target vehicle charging SoC percentage
    :return: a ranking (estimated travel + queue + charge time) for accessing the best-ranked charger
    """

    vehicle_mechatronics = env.mechatronics.get(vehicle.mechatronics_id)
    remaining_range = (
        vehicle_mechatronics.range_remaining_km(vehicle) if vehicle_mechatronics else 0.0
    )
    route = sim.road_network.route(vehicle.position, station.position)
    distance_km = route_distance_km(route)

    if not vehicle_mechatronics or remaining_range < distance_km:
        # vehicle does not have remaining range to reach this station
        # return a signal that demotes this Station alternative to the bottom of the ranking
        return None
    else:

        def _veh_at_station(v: Vehicle) -> bool:
            return (
                isinstance(v.vehicle_state, ChargingStation)
                and v.vehicle_state.station_id == station.id
            )

        def _veh_enqueued(v: Vehicle) -> bool:
            return (
                isinstance(v.vehicle_state, ChargeQueueing)
                and v.vehicle_state.station_id == station.id
            )

        def _time_to_full_by_charger_id(c: ChargerId):
            def _time_to_full(v: Vehicle) -> Seconds:
                _mech = env.mechatronics.get(v.mechatronics_id)
                _charger = env.chargers.get(c)
                if not _mech or not _charger:
                    return 0
                else:
                    max_iter = (
                        int(env.config.sim.end_time - sim.sim_time)
                        / sim.sim_timestep_duration_seconds
                    )
                    time_est = powercurve_ops.time_to_full(
                        v,
                        _mech,
                        _charger,
                        target_soc,
                        sim.sim_timestep_duration_seconds,
                        min_delta_energy_change=env.config.sim.min_delta_energy_change,
                        max_iterations=int(max_iter),
                    )
                    return time_est

            return _time_to_full

        def _sort_enqueue_time(v: Vehicle) -> Tuple[int, str]:
            if isinstance(v.vehicle_state, ChargeQueueing):
                enqueue_time = int(v.vehicle_state.enqueue_time)
            else:
                log.error(
                    "calling _sort_enqueue_time on a vehicle state that is not ChargeQueueing"
                )
                enqueue_time = 0
            return (enqueue_time, v.id)

        def _greedy_assignment(
            _charging: Tuple[Seconds, ...],
            _enqueued: Tuple[Seconds, ...],
            _charger_id: ChargerId,
            time_passed: Seconds = 0,
        ) -> Seconds:
            """
            computes the time estimated that a slot opens up for this vehicle to begin charging


            :param _charging: a sorted list of remaining charge time estimates
            :param _enqueued: a sorted list of charge time estimates for enqueued vehicles
            :param _charger_id: the id of the charger these vehicles are competing for
            :param time_passed: the amount of time that has been estimated
            :return: the time in the future we should expect to begin charging, determined by a greedy assignment
            """
            total_chargers = station.get_total_chargers(_charger_id)
            if total_chargers is None:
                log.error(f"charger id {_charger_id} not found at station {station.id}")
                total_chargers = 0

            if len(_charging) == len(_enqueued) == 0:
                return time_passed
            elif len(_charging) < total_chargers:
                return time_passed
            else:
                # advance time
                next_released_charger_time = TupleOps.head(_charging)

                updated_time_passed = time_passed + next_released_charger_time

                # remove charging agents who are done
                _charging_time_advanced = map(lambda t: t - next_released_charger_time, _charging)
                _charging_vacated = tuple(filter(lambda t: t > 0, _charging_time_advanced))

                vacancies = total_chargers - len(_charging_vacated)
                if vacancies <= 0:
                    # no space for any changes from enqueued -> charging
                    return _greedy_assignment(
                        _charging=_charging_vacated,
                        _enqueued=_enqueued,
                        _charger_id=_charger_id,
                        time_passed=updated_time_passed,
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
                        time_passed=updated_time_passed,
                    )

        # collect all vehicles that are either charging or enqueued at this station
        vehicles_at_station = sim.get_vehicles(filter_function=_veh_at_station)
        vehicles_enqueued = sim.get_vehicles(
            filter_function=_veh_enqueued,
            sort_key=_sort_enqueue_time,
        )

        estimates: Dict[ChargerId, int] = {}
        for charger_id in sorted(station.state.keys()):
            charger_state = station.state.get(charger_id)
            charger = charger_state.charger if charger_state is not None else None

            if charger is None or not vehicle_mechatronics.valid_charger(charger):
                # vehicle can't use this charger so we skip it
                continue

            # compute the charge time for the vehicle we are ranking
            max_iter = (
                int(env.config.sim.end_time - sim.sim_time) / sim.sim_timestep_duration_seconds
            )
            this_vehicle_charge_time = powercurve_ops.time_to_full(
                vehicle,
                vehicle_mechatronics,
                charger,
                target_soc,
                sim.sim_timestep_duration_seconds,
                min_delta_energy_change=env.config.sim.min_delta_energy_change,
                max_iterations=int(max_iter),
            )

            def _using_charger(charging_vehicle: Vehicle) -> bool:
                if isinstance(charging_vehicle.vehicle_state, ChargingStation):
                    if charging_vehicle.vehicle_state.charger_id == charger_id:
                        return True
                return False

            def _waiting_for_charger(enqueued_vehicle: Vehicle) -> bool:
                if isinstance(enqueued_vehicle.vehicle_state, ChargeQueueing):
                    if enqueued_vehicle.vehicle_state.charger_id == charger_id:
                        return True
                return False

            # collect all estimated remaining charge times for charging vehicles and sort them
            charging = filter(
                _using_charger,
                vehicles_at_station,
            )
            charging_time_to_full: Tuple[Seconds, ...] = tuple(
                sorted(map(_time_to_full_by_charger_id(charger_id), charging))
            )

            # collect estimated remaining charge times for vehicles enqueued for this charger
            # leave them sorted by enqueue time
            enqueued = filter(
                _waiting_for_charger,
                vehicles_enqueued,
            )
            enqueued_time_to_full: Tuple[Seconds, ...] = tuple(
                map(_time_to_full_by_charger_id(charger_id), enqueued)
            )

            # compute the estimated wait time to access a charger for the vehicle we are ranking
            wait_estimate_for_charger = _greedy_assignment(
                charging_time_to_full, enqueued_time_to_full, charger_id
            )

            # combine wait time with charge time
            overall_time_est = this_vehicle_charge_time + wait_estimate_for_charger
            estimates.update({charger_id: overall_time_est})

        if not estimates:
            # there are no chargers the vehicle can use.
            return None

        best_charger_id = min(estimates, key=estimates.__getitem__)

        # return the best "distance" aka shortest estimated time to finish charging
        best_overall_time = estimates[best_charger_id]
        dispatch_time_seconds = route_travel_time_seconds(route)
        return best_charger_id, dispatch_time_seconds + best_overall_time
