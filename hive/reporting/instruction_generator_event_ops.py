import h3

from hive.model.vehicle.vehicle import Vehicle
from hive.reporting.report_type import ReportType
from hive.reporting.reporter import Report
from hive.runner import Environment
from hive.util import wkt, SimTime


def refuel_search_event(vehicle: Vehicle, sim_time: SimTime, env: Environment) -> Report:
    """
    report that a vehicle is searching for a station to refuel
    :param vehicle: the vehicle seeking refueling
    :param sim_time: current simulation time
    :param env: the simulation environment
    :return: a report of this event
    """
    lat, lon = h3.h3_to_geo(vehicle.geoid)
    point_wkt  = wkt.point_2d((lat, lon), env.config.global_config.wkt_x_y_ordering)
    report = Report(
        report_type=ReportType.REFUEL_SEARCH_EVENT,
        report={
            'vehicle_id': vehicle.id,
            'vehicle_state': vehicle.vehicle_state.__class__.__name__,
            'sim_time': sim_time,
            'lat': lat,
            'lon': lon,
            'geoid': vehicle.geoid,
            'wkt': point_wkt
        }
    )
    return report
