from __future__ import annotations

from collections import Counter
from immutables import Map
import logging
import numpy as np
import os
import pandas as pd
from pandas import DataFrame
from pathlib import Path
from typing import TYPE_CHECKING, Callable, FrozenSet, List, Optional

from hive.reporting.handler.handler import Handler
from hive.reporting.report_type import ReportType
from hive.state.vehicle_state.vehicle_state_type import VehicleStateType

if TYPE_CHECKING:
    from hive.config import HiveConfig
    from hive.model.vehicle.vehicle import Vehicle
    from hive.runner.runner_payload import RunnerPayload
    from hive.reporting.reporter import Report
    from hive.util.typealiases import MembershipId

log = logging.getLogger(__name__)


class TimeStepStatsHandler(Handler):

    def __init__(self,
                 config: HiveConfig,
                 scenario_output_directory: Path,
                 fleet_ids: FrozenSet[MembershipId],
                 file_name: Optional[str] = "time_step_stats"):
        self.file_name = file_name

        self.start_time = config.sim.start_time
        self.timestep_duration_seconds = config.sim.timestep_duration_seconds

        self.vehicle_state_names = tuple(vs.name for vs in VehicleStateType)

        if config.global_config.log_time_step_stats:
            self.log_time_step_stats = True
            self.data = []
            self.time_step_stats_outpath = scenario_output_directory.joinpath(f"{file_name}_all.csv")
        else:
            self.log_time_step_stats = False

        if config.global_config.log_fleet_time_step_stats and len(fleet_ids) > 0:
            self.log_fleet_time_step_stats = True
            self.fleets_timestep_stats_outpath = scenario_output_directory.joinpath('fleet_time_step_stats/')
            self.fleets_data = {}
            for fleet_id in fleet_ids:
                self.fleets_data[fleet_id] = []
            self.fleets_data['none'] = []
        else:
            self.log_fleet_time_step_stats = False

    def get_time_step_stats(self) -> Optional[DataFrame]:
        """
        return a DataFrame of the time step level statistics.

        :return: the time step stats DataFrame
        """
        if not self.log_time_step_stats:
            return None

        return DataFrame(self.data)

    def get_fleet_time_step_stats(self) -> Optional[Map[MembershipId, DataFrame]]:
        """
        return an immutable map of time step stat DataFrames by membership id.

        :return: the immutable map containing time step stats DataFrames by membership id
        """
        if not self.log_fleet_time_step_stats:
            return None
        result = Map(
            {fleet_id: DataFrame(data) if len(data) > 0 else None for fleet_id, data in self.fleets_data.items()}
        )
        return result

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

        # sort reports by type
        reports_by_type = {}
        for report in reports:
            if report.report_type not in reports_by_type.keys():
                reports_by_type[report.report_type] = []
            reports_by_type[report.report_type].append(report)

        # get number of assigned requests in this time step
        assigned_requests_count = len(sim_state.get_requests(filter_function=lambda r: r.dispatched_vehicle is not None))

        # get number of active requests in this time step (unassigned)
        active_requests_count = len(sim_state.get_requests()) - assigned_requests_count

        # get number of canceled requests in this time step
        if ReportType.CANCEL_REQUEST_EVENT in reports_by_type.keys():
            canceled_requests_count = len(reports_by_type[ReportType.CANCEL_REQUEST_EVENT])
        else:
            canceled_requests_count = 0

        if self.log_time_step_stats:

            # grab all vehicles that are pooling
            veh_pooling = sim_state.get_vehicles(
                filter_function=lambda
                    v: v.vehicle_state.vehicle_state_type == VehicleStateType.SERVICING_POOLING_TRIP)

            # count the number of vehicles in each vehicle state
            veh_state_counts = Counter(
                map(
                    lambda v: v.vehicle_state.vehicle_state_type.name,
                    sim_state.get_vehicles()
                )
            )

            stats_row = {'time_step': time_step,
                         'sim_time': sim_time.as_iso_time()}

            # get average SOC of vehicles
            if len(sim_state.get_vehicles()) > 0:
                stats_row['avg_soc_percent'] = 100 * np.mean(
                    [env.mechatronics.get(v.mechatronics_id).fuel_source_soc(v) for v in sim_state.get_vehicles()]
                )
            else:
                stats_row['avg_soc_percent'] = None

            # get the total vkt
            if ReportType.VEHICLE_MOVE_EVENT in reports_by_type.keys():
                stats_row['vkt'] = sum(
                    [me.report['distance_km'] for me in reports_by_type[ReportType.VEHICLE_MOVE_EVENT]])
            else:
                stats_row['vkt'] = 0

            # add assigned request count
            stats_row['assigned_requests'] = assigned_requests_count

            # get number of active requests in this time step (unassigned)
            stats_row['active_requests'] = active_requests_count

            # get number of canceled requests in this time step
            stats_row['canceled_requests'] = canceled_requests_count

            # get count of requests currently being serviced by a vehicle
            pooling_request_count = sum([len(v.vehicle_state.boarded_requests)
                                         for v in veh_pooling])
            stats_row['servicing_requests'] = veh_state_counts[
                                                  VehicleStateType.SERVICING_TRIP.name] + pooling_request_count

            # add the number of vehicles in each vehicle state
            stats_row['vehicles'] = len(sim_state.vehicles)
            for state in self.vehicle_state_names:
                stats_row[f'vehicles_{state.lower()}'] = veh_state_counts[state]

            available_driver_counts = Counter(
                map(
                    lambda v: v.driver_state.available,
                    sim_state.get_vehicles()
                )
            )
            stats_row['drivers_available'] = available_driver_counts[True]
            stats_row['drivers_unavailable'] = available_driver_counts[False]

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

        if self.log_fleet_time_step_stats:
            for fleet_id in self.fleets_data.keys():

                def _get_veh_filter_func(membership_id: MembershipId) -> Callable[[Vehicle], bool]:
                    if membership_id == 'none':
                        return lambda v: not any(set(env.fleet_ids) & set(v.membership.memberships))
                    else:
                        return lambda v: fleet_id in v.membership.memberships

                def _get_report_filter_func(membership_id: MembershipId) -> Callable[[Report], bool]:
                    if membership_id == 'none':
                        return lambda r: not any(set(env.fleet_ids) & set(r.report['vehicle_memberships']))
                    else:
                        return lambda r: fleet_id in r.report['vehicle_memberships']

                # get vehicles in this fleet
                veh_in_fleet = sim_state.get_vehicles(
                    filter_function=_get_veh_filter_func(fleet_id)
                )

                # get vehicle reports in this fleet
                requests_in_fleet = {}
                for report_type in reports_by_type:
                    if report_type in (ReportType.VEHICLE_MOVE_EVENT, ReportType.VEHICLE_CHARGE_EVENT):
                        requests_in_fleet[report_type] = list(
                            filter(
                                _get_report_filter_func(fleet_id),
                                reports_by_type[report_type]
                            )
                        )

                # get vehicles pooling in this fleet
                veh_pooling_in_fleet = list(
                    filter(
                        lambda
                            v: v.vehicle_state.vehicle_state_type == VehicleStateType.SERVICING_POOLING_TRIP,
                        veh_in_fleet
                    )
                )

                # get vehicles dispatched to service pooling trips in this fleet
                veh_dispatch_pooling_in_fleet = list(
                    filter(
                        lambda
                            v: v.vehicle_state.vehicle_state_type == VehicleStateType.DISPATCH_POOLING_TRIP,
                        veh_in_fleet
                    )
                )

                # count the number of vehicles in each vehicle state in this fleet
                veh_state_counts_in_fleet = Counter(
                    map(
                        lambda v: v.vehicle_state.vehicle_state_type.name,
                        veh_in_fleet
                    )
                )

                # create stats row with the time step
                fleet_stats_row = {'time_step': time_step,
                                   'sim_time': sim_time.as_iso_time()}

                # get average SOC of vehicles in this fleet
                if len(veh_in_fleet) > 0:
                    fleet_stats_row['avg_soc_percent'] = 100 * np.mean(
                        [env.mechatronics.get(v.mechatronics_id).fuel_source_soc(v) for v in veh_in_fleet]
                    )
                else:
                    fleet_stats_row['avg_soc_percent'] = None

                # get the total vkt of vehicles in this fleet
                if ReportType.VEHICLE_MOVE_EVENT in requests_in_fleet.keys():
                    fleet_stats_row['vkt'] = sum([me.report['distance_km'] for me in requests_in_fleet[ReportType.VEHICLE_MOVE_EVENT]])
                else:
                    fleet_stats_row['vkt'] = 0

                # get number of assigned requests in this fleet
                assigned_requests = veh_state_counts_in_fleet[VehicleStateType.DISPATCH_TRIP.name]
                assigned_pooling_requests = sum([len(v.vehicle_state.trip_plan) for v in veh_dispatch_pooling_in_fleet])
                fleet_stats_row['assigned_requests'] = assigned_requests + assigned_pooling_requests

                # add number of active requests in this time step (unassigned)
                fleet_stats_row['active_requests'] = active_requests_count

                # add number of canceled requests in this time step
                fleet_stats_row['canceled_requests'] = canceled_requests_count

                # get count of requests currently being serviced by a vehicle
                servicing_requests = veh_state_counts_in_fleet[VehicleStateType.SERVICING_TRIP.name]
                servicing_pooling_requests = sum([len(v.vehicle_state.boarded_requests) for v in veh_pooling_in_fleet])
                fleet_stats_row['servicing_requests'] = servicing_requests + servicing_pooling_requests

                # add the number of vehicles in each vehicle state in this fleet
                fleet_stats_row['vehicles'] = len(veh_in_fleet)
                for state in self.vehicle_state_names:
                    fleet_stats_row[f'vehicles_{state.lower()}'] = veh_state_counts_in_fleet[state]

                available_driver_counts_in_fleet = Counter(
                    map(
                        lambda v: v.driver_state.available,
                        veh_in_fleet
                    )
                )
                fleet_stats_row['drivers_available'] = available_driver_counts_in_fleet[True]
                fleet_stats_row['drivers_unavailable'] = available_driver_counts_in_fleet[False]

                # count number of chargers in use by type
                if ReportType.VEHICLE_CHARGE_EVENT in requests_in_fleet.keys():
                    charger_counts_in_fleet = Counter(
                        map(
                            lambda r: r.report['charger_id'],
                            requests_in_fleet[ReportType.VEHICLE_CHARGE_EVENT]
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
        saves all time step stat DataFrames as csv files to the scenario output directory.

        :return:
        """
        if self.log_time_step_stats:
            pd.DataFrame.to_csv(self.get_time_step_stats(), self.time_step_stats_outpath, index=False)
            log.info(f"time step stats written to {self.time_step_stats_outpath}")

        if self.log_fleet_time_step_stats:
            os.mkdir(self.fleets_timestep_stats_outpath)
            for fleet_id, fleet_df in self.get_fleet_time_step_stats().items():
                if fleet_df is not None:
                    outpath = self.fleets_timestep_stats_outpath.joinpath(f'{self.file_name}_{fleet_id}.csv')
                    pd.DataFrame.to_csv(fleet_df, outpath, index=False)
                    log.info(f"fleet id: {fleet_id} time step stats written to {outpath}")
