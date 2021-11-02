from __future__ import annotations

from collections import Counter
import logging
import numpy as np
import pandas as pd
from pathlib import Path
from typing import TYPE_CHECKING, FrozenSet, List

from hive.reporting.handler.handler import Handler
from hive.reporting.report_type import ReportType
from hive.state.vehicle_state.vehicle_state_type import VehicleStateType

if TYPE_CHECKING:
    from hive.config import HiveConfig
    from hive.model.membership import MembershipId
    from hive.runner.runner_payload import RunnerPayload
    from hive.reporting.reporter import Report

log = logging.getLogger(__name__)


class TimeStepStatsHandler(Handler):

    def __init__(self, config: HiveConfig, scenario_output_directory: Path, fleet_ids: FrozenSet[MembershipId]):
        self.global_config = config.global_config

        self.start_time = config.sim.start_time
        self.timestep_duration_seconds = config.sim.timestep_duration_seconds

        self.vehicle_state_names = tuple(vs.name for vs in VehicleStateType)

        if self.global_config.log_time_step_stats:
            self.data = []
            self.timestep_stats_outpath = scenario_output_directory.joinpath("time_step_stats.csv")

        if self.global_config.log_fleet_time_step_stats:
            self.fleets_timestep_stats_outpath = scenario_output_directory.joinpath('fleet_time_step_stats/')
            self.fleets_data = {}
            for fleet_id in fleet_ids:
                self.fleets_data[fleet_id] = []

    def handle(self, reports: List[Report], runner_payload: RunnerPayload):
        """
        called at each log step. aggregates various statistics to the time bin level

        :param reports: reports for gathering statistics

        :param runner_payload
        :return:
        """

        sim_state = runner_payload.s
        env = runner_payload.e

        # get the time step
        sim_time = sim_state.sim_time
        time_step = int((sim_time.as_epoch_time() - self.start_time.as_epoch_time()) / self.timestep_duration_seconds)

        reports_by_type = {}
        for report in reports:
            if report.report_type not in reports_by_type.keys():
                reports_by_type[report.report_type] = []
            reports_by_type[report.report_type].append(report)

        # get number of assigned requests in this time step
        assigned_requests = sim_state.get_requests(filter_function=lambda r: r.dispatched_vehicle is not None)

        # grab all vehicles that are pooling
        vehicles_pooling = sim_state.get_vehicles(
            filter_function=lambda
                v: v.vehicle_state.vehicle_state_type == VehicleStateType.SERVICING_POOLING_TRIP)

        if self.global_config.log_time_step_stats:
            stats_row = {'time_step': time_step}

            # get average SOC of vehicles
            stats_row['avg_soc_percent'] = round(100 * np.mean([
                env.mechatronics.get(v.mechatronics_id).fuel_source_soc(v) for v in sim_state.vehicles.values()
            ]), 2)

            # get the total vkt
            if ReportType.VEHICLE_MOVE_EVENT in reports_by_type.keys():
                stats_row['vkt'] = sum([me.report['distance_km'] for me in reports_by_type[ReportType.VEHICLE_MOVE_EVENT]])
            else:
                stats_row['vkt'] = 0

            # add assigned request count
            stats_row['assigned_requests'] = len(assigned_requests)

            # get number of active requests in this time step (unassigned)
            stats_row['active_requests'] = len(sim_state.get_requests()) - len(assigned_requests)

            # get number of canceled requests in this time step
            if ReportType.CANCEL_REQUEST_EVENT in reports_by_type.keys():
                stats_row['canceled_requests'] = len(reports_by_type[ReportType.CANCEL_REQUEST_EVENT])
            else:
                stats_row['canceled_requests'] = 0

            vehicle_state_counts = Counter(
                map(
                    lambda v: v.vehicle_state.vehicle_state_type.name,
                    sim_state.get_vehicles()
                )
            )

            # get count of requests currently being serviced by a vehicle
            pooling_request_count = sum([len(v.vehicle_state.boarded_requests) for v in vehicles_pooling])
            stats_row['servicing_requests'] = vehicle_state_counts[
                                                VehicleStateType.SERVICING_TRIP.name] + pooling_request_count

            # count the number of vehicles in each vehicle state
            for state in self.vehicle_state_names:
                stats_row[f'vehicles_{state.lower()}'] = vehicle_state_counts[state]

            # count number of chargers in use by type
            if ReportType.VEHICLE_CHARGE_EVENT in reports_by_type.keys():
                charger_counts = Counter(
                    map(
                        lambda r: r.report['charger_id'],
                        reports_by_type[ReportType.VEHICLE_CHARGE_EVENT]
                    )
                )
                for charger in env.chargers.keys():
                    stats_row[f'charger_{charger.lower()}'] = charger_counts[charger]
            else:
                for charger in env.chargers.keys():
                    stats_row[f'charger_{charger.lower()}'] = 0

            # append the statistics row to the data list
            self.data.append(stats_row)

        if self.global_config.log_fleet_time_step_stats:
            for fleet_id in self.fleets_data.keys():

                # create stats row with the time step
                fleet_stats_row = {'time_step': time_step}

                # get vehicles in this fleet
                veh_in_fleet = sim_state.get_vehicles(filter_function=lambda v: fleet_id in v.membership.memberships)

                # get average SOC of vehicles in this fleet
                fleet_stats_row['avg_soc_percent'] = round(100 * np.mean([
                    env.mechatronics.get(v.mechatronics_id).fuel_source_soc(v) for v in veh_in_fleet]), 2)

                # get the total vkt of vehicles in this fleet
                if ReportType.VEHICLE_MOVE_EVENT in reports_by_type.keys():
                    move_events_in_fleet = list(
                        filter(
                            lambda r: fleet_id in env.vehicle_fleet_ids[r.report['vehicle_id']],
                            reports_by_type[ReportType.VEHICLE_MOVE_EVENT]
                        )
                    )
                    fleet_stats_row['vkt'] = sum([me.report['distance_km'] for me in move_events_in_fleet])
                else:
                    fleet_stats_row['vkt'] = 0

                # get number of assigned requests in this fleet
                fleet_stats_row['assigned_requests'] = len(list(
                        filter(
                            lambda r: fleet_id in env.vehicle_fleet_ids[r.dispatched_vehicle],
                            assigned_requests
                        )
                    ))
                # Todo: should these be based on the request membership or the vehicle membership
                # get number of active requests in this time step (unassigned)
                fleet_stats_row['active_requests'] = len(sim_state.get_requests()) - len(assigned_requests)

                # get number of canceled requests in this time step
                if ReportType.CANCEL_REQUEST_EVENT in reports_by_type.keys():
                    fleet_stats_row['canceled_requests'] = len(reports_by_type[ReportType.CANCEL_REQUEST_EVENT])
                else:
                    fleet_stats_row['canceled_requests'] = 0

                vehicle_state_counts_in_fleet = Counter(
                    map(
                        lambda v: v.vehicle_state.vehicle_state_type.name,
                        veh_in_fleet
                    )
                )
                vehicles_pooling_in_fleet = list(
                    filter(
                        lambda v: fleet_id in env.vehicle_fleet_ids[v.id],
                        vehicles_pooling
                    )
                )

                # get count of requests currently being serviced by a vehicle
                pooling_request_count = sum([len(v.vehicle_state.boarded_requests) for v in vehicles_pooling_in_fleet])
                fleet_stats_row['servicing_requests'] = vehicle_state_counts_in_fleet[
                                                            VehicleStateType.SERVICING_TRIP.name] + pooling_request_count

                # count the number of vehicles in each vehicle state in this fleet
                for state in self.vehicle_state_names:
                    fleet_stats_row[f'vehicles_{state.lower()}'] = vehicle_state_counts_in_fleet[state]

                # count number of chargers in use by type
                if ReportType.VEHICLE_CHARGE_EVENT in reports_by_type.keys():
                    charge_events_in_fleet = list(
                        filter(
                            lambda r: fleet_id in env.vehicle_fleet_ids[r.report['vehicle_id']],
                            reports_by_type[ReportType.VEHICLE_CHARGE_EVENT]
                        )
                    )
                    charger_counts_in_fleet = Counter(
                        map(
                            lambda r: r.report['charger_id'],
                            charge_events_in_fleet
                        )
                    )
                    for charger in env.chargers.keys():
                        fleet_stats_row[f'charger_{charger.lower()}'] = charger_counts_in_fleet[charger]
                else:
                    for charger in env.chargers.keys():
                        fleet_stats_row[f'charger_{charger.lower()}'] = 0

                # append the statistics row to the fleet's data list
                self.fleets_data[fleet_id].append(fleet_stats_row)

    def close(self, runner_payload: RunnerPayload):
        """
        saves the time step stats dataframe as a csv file to the scenario output directory

        :return:
        """
        if self.global_config.log_time_step_stats:
            pd.DataFrame.to_csv(pd.DataFrame(self.data), self.timestep_stats_outpath, index=False)
            log.info(f"time step stats written to {self.timestep_stats_outpath}")

        if self.global_config.log_fleet_time_step_stats:
            self.fleets_timestep_stats_outpath.mkdir(parents=True)
            for fleet_id, fleet_data in self.fleets_data.items():
                pd.DataFrame.to_csv(pd.DataFrame(fleet_data),
                                    self.fleets_timestep_stats_outpath.joinpath(f'time_step_stats_{fleet_id}.csv'),
                                    index=False)
