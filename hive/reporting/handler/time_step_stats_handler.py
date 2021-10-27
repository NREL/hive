from __future__ import annotations

from collections import Counter
import numpy as np
import pandas as pd
from pathlib import Path
from typing import TYPE_CHECKING, List

from hive.reporting.handler.handler import Handler
from hive.reporting.report_type import ReportType
from hive.state.vehicle_state.vehicle_state_type import VehicleStateType

if TYPE_CHECKING:
    from hive.config import HiveConfig
    from hive.runner.runner_payload import RunnerPayload
    from hive.reporting.reporter import Report


class TimeStepStatsHandler(Handler):

    def __init__(self, config: HiveConfig, scenario_output_directory: Path):
        self.csv_path = scenario_output_directory / 'time_step_stats.csv'

        self.start_time = config.sim.start_time
        self.timestep_duration_seconds = config.sim.timestep_duration_seconds

        self.vehicle_state_names = tuple(vs.name for vs in VehicleStateType)

        self.frame = pd.DataFrame(
            columns=['time_step',
                     'avg_soc_percent',
                     'vkt',
                     'active_requests',
                     'canceled_requests',
                     'assigned_requests',
                     'servicing_requests'])

    def handle(self, reports: List[Report], runner_payload: RunnerPayload):
        """
        called at each log step. aggregates various statistics to the time bin level in a dataframe


        :param reports:

        :param runner_payload
        :return:
        """

        stats_dict = {}

        sim_state = runner_payload.s
        env = runner_payload.e
        sim_time = sim_state.sim_time
        stats_dict['time_step'] = int((sim_time.as_epoch_time() - self.start_time.as_epoch_time()) /
                                      self.timestep_duration_seconds)

        # count number of reports by type
        c = Counter(map(lambda r: r.report_type, reports))

        # get average SOC of vehicles
        stats_dict['avg_soc_percent'] = round(100 * np.mean([
            env.mechatronics.get(v.mechatronics_id).fuel_source_soc(v) for v in sim_state.vehicles.values()
        ]), 2)

        # get the total vkt
        move_events = list(
            filter(
                lambda r: r.report_type == ReportType.VEHICLE_MOVE_EVENT,
                reports
            )
        )
        stats_dict['vkt'] = sum([me.report['distance_km'] for me in move_events])

        # get number of assigned requests in this time step
        assigned_requests = sim_state.get_requests(filter_function=lambda r: r.dispatched_vehicle is not None)
        stats_dict['assigned_requests'] = len(assigned_requests)

        # get number of active requests in this time step (unassigned)
        stats_dict['active_requests'] = len(sim_state.get_requests()) - len(assigned_requests)

        # get number of canceled requests in this time step
        stats_dict['canceled_requests'] = c[ReportType.CANCEL_REQUEST_EVENT]

        # count the number of vehicles in each vehicle state
        vehicle_state_counts = Counter(
            map(
                lambda v: v.vehicle_state.vehicle_state_type.name,
                sim_state.get_vehicles()
            )
        )
        for state in self.vehicle_state_names:
            stats_dict[f'vehicles_{state.lower()}'] = vehicle_state_counts[state]

        # get count of requests currently being serviced by a vehicle
        vehicles_pooling = sim_state.get_vehicles(
            filter_function=lambda v: v.vehicle_state.vehicle_state_type == VehicleStateType.SERVICING_POOLING_TRIP)
        pooling_request_count = 0
        for veh in vehicles_pooling:
            pooling_request_count += len(veh.vehicle_state.boarded_requests)
        stats_dict['servicing_requests'] = vehicle_state_counts[VehicleStateType.SERVICING_TRIP.name] + pooling_request_count

        # count number of chargers in use by type
        charge_event_reports = list(
            filter(
                lambda r: r.report_type == ReportType.VEHICLE_CHARGE_EVENT,
                reports
            )
        )
        charger_counts = Counter(
            map(
                lambda r: r.report['charger_id'],
                charge_event_reports
            )
        )
        for charger in env.chargers.keys():
            stats_dict[f'charger_{charger.lower()}'] = charger_counts[charger]

        # add the statistics to the dataframe
        self.frame = self.frame.append(stats_dict, ignore_index=True)

    def close(self, runner_payload: RunnerPayload):
        """
        saves the time step stats dataframe as a csv file to the scenario output directory

        :return:
        """
        pd.DataFrame.to_csv(self.frame, self.csv_path, index=False)
