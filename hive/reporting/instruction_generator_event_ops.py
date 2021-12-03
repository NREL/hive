from __future__ import annotations
from typing import TYPE_CHECKING

import h3

from hive.reporting.report_type import ReportType
from hive.reporting.reporter import Report
from hive.util import wkt

if TYPE_CHECKING:
    from hive.model.vehicle.vehicle import Vehicle
    from hive.runner import Environment
    from hive.state.simulation_state.simulation_state import SimulationState


def refuel_search_event(vehicle: Vehicle, sim: SimulationState, env: Environment) -> Report:
    """
    report that a vehicle is searching for a station to refuel

    :param vehicle: the vehicle seeking refueling
    :param sim: the simulation state before the search event
    :param env: the simulation environment
    :return: a report of this event
    """
    lat, lon = h3.h3_to_geo(vehicle.geoid)
    point_wkt = wkt.point_2d((lat, lon), env.config.global_config.wkt_x_y_ordering)
    next_sim_time = sim.sim_time + sim.sim_timestep_duration_seconds
    report = Report(
        report_type=ReportType.REFUEL_SEARCH_EVENT,
        report={
            'vehicle_id': vehicle.id,
            'vehicle_state': vehicle.vehicle_state.__class__.__name__,
            'vehicle_memberships': vehicle.membership.to_json(),
            'sim_time_start': sim.sim_time,
            'sim_time_end': next_sim_time,
            'lat': lat,
            'lon': lon,
            'geoid': vehicle.geoid,
            'wkt': point_wkt
        }
    )
    return report
