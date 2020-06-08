import functools as ft
from typing import Dict

from h3 import h3

from hive.model.energy import EnergyType, Charger
from hive.model.roadnetwork import route
from hive.model.station import Station
from hive.model.vehicle import Vehicle
from hive.state.simulation_state.simulation_state import SimulationState
from hive.util.typealiases import ChargerId


def make_report(report_type: str, report_data: Dict) -> Dict:
    """
    a helper for those who forget the key of the "report_type" field
    :param report_type: the report type
    :param report_data: the data to report
    :return: a report of this report_type
    """
    report = {'report_type': report_type}
    report.update(report_data)
    return report


def vehicle_move_report(move_result: 'MoveResult') -> Dict:
    """
    creates a vehicle move report based on the effect of one time step of moving
    :param move_result: the result of a move
    :return: the vehicle move report
    """
    sim_time = move_result.sim.sim_time
    duration = move_result.sim.sim_timestep_duration_seconds
    vehicle_id = move_result.next_vehicle.id
    vehicle_state = move_result.next_vehicle.vehicle_state.__class__.__name__
    delta_distance: float = move_result.next_vehicle.distance_traveled_km - move_result.prev_vehicle.distance_traveled_km
    delta_energy = ft.reduce(
        lambda acc, e_type: acc + move_result.next_vehicle.energy.get(e_type) - move_result.prev_vehicle.energy.get(e_type),
        move_result.next_vehicle.energy.keys(),
        0
    )
    geoid = move_result.next_vehicle.geoid
    lat, lon = h3.h3_to_geo(geoid)
    geom = route.to_linestring(move_result.route_traversal.experienced_route)
    report_data = {
        'sim_time': sim_time,
        'duration_sec': duration,
        'vehicle_id': vehicle_id,
        'vehicle_state': vehicle_state,
        'distance_km': delta_distance,
        'energy_kwh': delta_energy,
        'geoid': geoid,
        'lat': lat,
        'lon': lon,
        'route_wkt': geom
    }
    report = make_report("vehicle_move_event", report_data)
    return report


def vehicle_charge_report(prev_vehicle: Vehicle,
                          next_vehicle: Vehicle,
                          next_sim: SimulationState,
                          station: Station,
                          charger_id: ChargerId) -> Dict:
    """
    reports information about the marginal effect of a charge event
    :param prev_vehicle: the previous vehicle state
    :param next_vehicle: the next vehicle state
    :param next_sim: the next simulation state after the charge event
    :param station: the station involved with the charge event
    :param charger_id: the charger_id type used
    :return: a charge event report
    """

    sim_time = next_sim.sim_time
    duration = next_sim.sim_timestep_duration_seconds
    vehicle_id = next_vehicle.id
    station_id = station.id
    vehicle_state = next_vehicle.vehicle_state.__class__.__name__
    kwh_transacted = next_vehicle.energy[EnergyType.ELECTRIC] - prev_vehicle.energy[EnergyType.ELECTRIC]  # kwh
    charger_price = station.charger_prices_per_kwh.get(charger_id)  # Currency
    charging_price = kwh_transacted * charger_price if charger_price else 0.0

    geoid = next_vehicle.geoid
    lat, lon = h3.h3_to_geo(geoid)

    report_data = {
        'sim_time': sim_time,
        'duration_sec': duration,
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

    report = make_report("vehicle_charge_event", report_data)
    return report
