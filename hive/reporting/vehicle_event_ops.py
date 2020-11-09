from __future__ import annotations

import functools as ft
from typing import TYPE_CHECKING, Tuple, Set

import h3
import immutables

from hive.model.energy import Charger
from hive.model.roadnetwork import route
from hive.model.station import Station
from hive.model.vehicle.vehicle import Vehicle
from hive.reporting.reporter import Report, ReportType
from hive.runner import Environment
from hive.state.simulation_state.simulation_state import SimulationState
from hive.util import StationId
from hive.util.time_helpers import time_diff

if TYPE_CHECKING:
    from hive.model.request.request import Request
    from hive.state.vehicle_state.vehicle_state_ops import MoveResult


def vehicle_move_event(move_result: MoveResult, env: Environment) -> Report:
    """
    creates a vehicle move report based on the effect of one time step of moving

    :param move_result: the result of a move
    :param env: the simulation environment
    :return: the vehicle move report
    """
    sim_time_start = move_result.sim.sim_time - move_result.sim.sim_timestep_duration_seconds
    sim_time_end = move_result.sim.sim_time
    vehicle_id = move_result.next_vehicle.id
    vehicle_state = move_result.prev_vehicle.vehicle_state.__class__.__name__
    delta_distance: float = move_result.next_vehicle.distance_traveled_km - move_result.prev_vehicle.distance_traveled_km
    delta_energy = ft.reduce(
        lambda acc, e_type: acc + move_result.next_vehicle.energy.get(e_type) - move_result.prev_vehicle.energy.get(
            e_type),
        move_result.next_vehicle.energy.keys(),
        0
    )
    if len(move_result.next_vehicle.energy.keys()) > 1:
        raise NotImplemented("hive doesn't currently support multiple energy types")
    else:
        energy_units = list(move_result.next_vehicle.energy.keys())[0].units

    geoid = move_result.next_vehicle.geoid
    lat, lon = h3.h3_to_geo(geoid)
    geom = route.to_linestring(move_result.route_traversal.experienced_route, env)
    report_data = {
        'sim_time_start': sim_time_start,
        'sim_time_end': sim_time_end,
        'vehicle_id': vehicle_id,
        'vehicle_state': vehicle_state,
        'distance_km': delta_distance,
        'energy': delta_energy,
        'energy_units': energy_units,
        'geoid': geoid,
        'lat': lat,
        'lon': lon,
        'route_wkt': geom
    }
    report = Report(ReportType.VEHICLE_MOVE_EVENT, report_data)
    return report


def vehicle_charge_event(prev_vehicle: Vehicle,
                         next_vehicle: Vehicle,
                         next_sim: SimulationState,
                         station: Station,
                         charger: Charger,
                         ) -> Report:
    """
    reports information about the marginal effect of a charge event

    :param prev_vehicle: the previous vehicle state
    :param next_vehicle: the next vehicle state
    :param next_sim: the next simulation state after the charge event
    :param station: the station involved with the charge event (either before or after update)
    :param charger: the charger used
    :return: a charge event report
    """

    sim_time_start = next_sim.sim_time - next_sim.sim_timestep_duration_seconds
    sim_time_end = next_sim.sim_time
    vehicle_id = next_vehicle.id
    station_id = station.id
    vehicle_state = prev_vehicle.vehicle_state.__class__.__name__
    energy_transacted = next_vehicle.energy[charger.energy_type] - prev_vehicle.energy[charger.energy_type]  # kwh
    charger_price = station.charger_prices_per_kwh.get(charger.id)  # Currency
    charging_price = energy_transacted * charger_price if charger_price else 0.0

    geoid = next_vehicle.geoid
    lat, lon = h3.h3_to_geo(geoid)

    report_data = {
        'sim_time_start': sim_time_start,
        'sim_time_end': sim_time_end,
        'vehicle_id': vehicle_id,
        'station_id': station_id,
        'vehicle_state': vehicle_state,
        'energy': energy_transacted,
        'energy_units': charger.energy_type.units,
        'price': charging_price,
        'charger_id': charger.id,
        'geoid': geoid,
        'lat': lat,
        'lon': lon
    }

    report = Report(ReportType.VEHICLE_CHARGE_EVENT, report_data)
    return report


def report_pickup_request(vehicle: Vehicle,
                          request: Request,
                          next_sim: SimulationState,
                          ) -> Report:
    """
    reports information about the marginal effect of a request pickup

    :param vehicle: the vehicle that picked up the request
    :param request: the request that was picked up
    :param next_sim: the next simulation state after the request pickup
    :return: a pickup request report
    """

    event_sim_time = next_sim.sim_time - next_sim.sim_timestep_duration_seconds

    geoid = vehicle.geoid
    lat, lon = h3.h3_to_geo(geoid)
    wait_time = time_diff(request.departure_time.as_datetime_time(), event_sim_time.as_datetime_time())

    report_data = {
        'pickup_time': event_sim_time,
        'request_time': request.departure_time,
        'wait_time_seconds': wait_time,
        'vehicle_id': vehicle.id,
        'request_id': request.id,
        'request_membership': request.membership,
        'price': request.value,
        'geoid': geoid,
        'lat': lat,
        'lon': lon
    }

    report = Report(ReportType.PICKUP_REQUEST_EVENT, report_data)
    return report


def report_dropoff_request(vehicle: Vehicle,
                           sim: SimulationState,
                           ) -> Report:
    """
    reports information about the marginal effect of a request dropoff
    :param vehicle: the vehicle that picked up the request
    :param sim: simulation state when the dropoff occurs
    :return: a dropoff request report
    """

    geoid = vehicle.geoid
    lat, lon = h3.h3_to_geo(geoid)
    travel_time = time_diff(vehicle.vehicle_state.departure_time.as_datetime_time(), sim.sim_time.as_datetime_time())

    report_data = {
        'dropoff_time': sim.sim_time,
        'travel_time': travel_time,
        'vehicle_id': vehicle.id,
        'request_id': vehicle.vehicle_state.request_id,
        'geoid': geoid,
        'lat': lat,
        'lon': lon
    }

    report = Report(ReportType.DROPOFF_REQUEST_EVENT, report_data)
    return report


def construct_station_load_events(reports: Tuple[Report], sim: SimulationState) -> Tuple[Report, ...]:
    """
    a station load report takes any vehicle charge events and attributes them to a
    station, so that, for each time step, we report the load of energy use at the station

    :param reports: the reports in this time step
    :param sim: the simulation state
    :return: a collection with one STATION_LOAD_EVENT per StationId
    """
    sim_time_start = sim.sim_time - sim.sim_timestep_duration_seconds
    sim_time_end = sim.sim_time

    def _add(acc: immutables.Map, report: Report) -> immutables.Map:
        """
        if the report has charging information, then add it to the accumulator.
        /
        expects that all reports fall between the same range of [sim_time_start, sim_time_end]

        :param acc: a mapping from station to current load
        :param report: a report of any type
        :return: the updated accumulator
        """
        if report.report_type != ReportType.VEHICLE_CHARGE_EVENT:
            return acc
        else:
            station_id = report.report['station_id']
            energy = float(report.report['energy'])
            energy_units = report.report['energy_units']
            station_energy, _ = acc.get(station_id, (0.0, ""))
            updated_energy = station_energy + energy
            updated_acc = acc.update({station_id: (updated_energy, energy_units)})

            return updated_acc

    def _to_reports(acc: immutables.Map[StationId, float]) -> Tuple[Report, ...]:
        """
        transforms the accumulated values into Reports
        :return: a collection of STATION_LOAD_EVENT reports
        """

        def _cast_as_report(station_id: StationId):
            energy, energy_units = acc.get(station_id)
            report = Report(
                report_type=ReportType.STATION_LOAD_EVENT,
                report={
                    "station_id": station_id,
                    "sim_time_start": sim_time_start,
                    "sim_time_end": sim_time_end,
                    "energy": energy,
                    "energy_units": energy_units,
                }
            )
            return report

        these_reports: Tuple[Report, ...] = tuple(map(_cast_as_report, acc.keys()))
        return these_reports

    # collect vehicle charge events
    reported_charge_events_accumulator = ft.reduce(_add, reports, immutables.Map())

    # create entries for stations with no charge events reported
    reported_stations: Set[StationId] = set(reported_charge_events_accumulator.keys())
    unreported_station_ids: Set[StationId] = set(sim.stations.keys()).difference(reported_stations)
    all_stations_accumulator = ft.reduce(
        lambda acc, id: acc.update({id: (0.0, "")}),
        unreported_station_ids,
        reported_charge_events_accumulator
    )

    result = _to_reports(all_stations_accumulator)

    return result
