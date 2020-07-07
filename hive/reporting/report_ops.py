from __future__ import annotations

import functools as ft
from typing import TYPE_CHECKING

from h3 import h3

from hive.model.energy import EnergyType
from hive.model.roadnetwork import route
from hive.model.station import Station
from hive.model.vehicle import Vehicle
from hive.reporting.reporter import Report, ReportType
from hive.state.simulation_state.simulation_state import SimulationState
from hive.util.typealiases import ChargerId

if TYPE_CHECKING:
    from hive.model.request.request import Request
    from hive.state.vehicle_state.vehicle_state_ops import MoveResult


def vehicle_move_event(move_result: MoveResult) -> Report:
    """
    creates a vehicle move report based on the effect of one time step of moving
    :param move_result: the result of a move
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
    geoid = move_result.next_vehicle.geoid
    lat, lon = h3.h3_to_geo(geoid)
    geom = route.to_linestring(move_result.route_traversal.experienced_route)
    report_data = {
        'sim_time_start': sim_time_start,
        'sim_time_end': sim_time_end,
        'vehicle_id': vehicle_id,
        'vehicle_state': vehicle_state,
        'distance_km': delta_distance,
        'energy_kwh': delta_energy,
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
                         charger_id: ChargerId) -> Report:
    """
    reports information about the marginal effect of a charge event
    :param prev_vehicle: the previous vehicle state
    :param next_vehicle: the next vehicle state
    :param next_sim: the next simulation state after the charge event
    :param station: the station involved with the charge event
    :param charger_id: the charger_id type used
    :return: a charge event report
    """

    sim_time_start = next_sim.sim_time - next_sim.sim_timestep_duration_seconds
    sim_time_end = next_sim.sim_time
    vehicle_id = next_vehicle.id
    station_id = station.id
    vehicle_state = prev_vehicle.vehicle_state.__class__.__name__
    kwh_transacted = next_vehicle.energy[EnergyType.ELECTRIC] - prev_vehicle.energy[EnergyType.ELECTRIC]  # kwh
    charger_price = station.charger_prices_per_kwh.get(charger_id)  # Currency
    charging_price = kwh_transacted * charger_price if charger_price else 0.0

    geoid = next_vehicle.geoid
    lat, lon = h3.h3_to_geo(geoid)

    report_data = {
        'sim_time_start': sim_time_start,
        'sim_time_end': sim_time_end,
        'vehicle_id': vehicle_id,
        'station_id': station_id,
        'vehicle_state': vehicle_state,
        'energy_kwh': kwh_transacted,
        'price': charging_price,
        'charger_id': charger_id,
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

    sim_time_start = next_sim.sim_time - next_sim.sim_timestep_duration_seconds

    geoid = vehicle.geoid
    lat, lon = h3.h3_to_geo(geoid)

    report_data = {
        'pickup_time': sim_time_start,
        'request_time': request.departure_time,
        'wait_time_seconds': sim_time_start - request.departure_time,
        'vehicle_id': vehicle.id,
        'request_id': request.id,
        'price': request.value,
        'geoid': geoid,
        'lat': lat,
        'lon': lon
    }

    report = Report(ReportType.PICKUP_REQUEST_EVENT, report_data)
    return report