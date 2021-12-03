import h3
from hive.model.vehicle.vehicle import Vehicle
from hive.reporting.report_type import ReportType
from hive.reporting.reporter import Report
from hive.runner import Environment
from hive.util import wkt
from enum import Enum


class ScheduleEventType(Enum):
    OFF = "off"
    ON = "on"


def driver_schedule_event(sim: 'SimulationState',
                          env: Environment,
                          vehicle: Vehicle,
                          schedule_event: ScheduleEventType) -> Report:

    lat, lon = h3.h3_to_geo(vehicle.geoid)
    point_wkt = wkt.point_2d((lat, lon), env.config.global_config.wkt_x_y_ordering)
    next_sim_time = sim.sim_time + sim.sim_timestep_duration_seconds

    report_data = {
        'vehicle_id': vehicle.id,
        'vehicle_state': vehicle.vehicle_state.__class__.__name__,
        'vehicle_memberships': vehicle.membership.to_json(),
        'sim_time_start': sim.sim_time,
        'sim_time_end': next_sim_time,
        'lat': lat,
        'lon': lon,
        'geoid': vehicle.geoid,
        'wkt': point_wkt,
        'schedule_event': schedule_event.value
    }

    report = Report(ReportType.DRIVER_SCHEDULE_EVENT, report_data)

    return report
