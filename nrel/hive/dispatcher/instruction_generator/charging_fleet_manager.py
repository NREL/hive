from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Tuple, TYPE_CHECKING

from nrel.hive.reporting import instruction_generator_event_ops
from nrel.hive.state.vehicle_state.idle import Idle
from nrel.hive.state.vehicle_state.repositioning import Repositioning

if TYPE_CHECKING:
    from nrel.hive.model.vehicle.vehicle import Vehicle
    from nrel.hive.state.simulation_state.simulation_state import SimulationState
    from nrel.hive.runner.environment import Environment
    from nrel.hive.dispatcher.instruction.instruction import Instruction
    from nrel.hive.config.dispatcher_config import DispatcherConfig

from nrel.hive.dispatcher.instruction_generator.instruction_generator import InstructionGenerator
from nrel.hive.dispatcher.instruction_generator.instruction_generator_ops import (
    instruct_vehicles_to_dispatch_to_station,
    get_nearest_valid_station_distance,
)

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class ChargingFleetManager(InstructionGenerator):
    """
    A manager that instructs vehicles to charge if they fall below an SOC threshold.
    """

    config: DispatcherConfig

    def generate_instructions(
        self,
        simulation_state: SimulationState,
        environment: Environment,
    ) -> Tuple[ChargingFleetManager, Tuple[Instruction, ...]]:
        """
        Generate fleet targets for the dispatcher to execute based on the simulation state.


        :param simulation_state: The current simulation state
        :param environment: The simulation environment
        :return: the updated ChargingFleetManager along with instructions
        """

        # find vehicles that fall below the sum of the threshold distance and nearest valid station distance

        def charge_candidate(v: Vehicle) -> bool:
            proper_state = isinstance(v.vehicle_state, Idle) or isinstance(
                v.vehicle_state, Repositioning
            )
            if not proper_state:
                return False

            mechatronics = environment.mechatronics.get(v.mechatronics_id)
            if mechatronics is None:
                log.error(f"mechatronics {v.mechatronics_id} missing for vehicle {v.id}")
                return False

            range_remaining_km = mechatronics.range_remaining_km(v)
            if range_remaining_km > environment.config.dispatcher.charging_range_km_soft_threshold:
                # don't even check station distance if vehicle range is over soft threshold
                return False

            nearest_station_distance = get_nearest_valid_station_distance(
                max_search_radius_km=self.config.max_search_radius_km,
                vehicle=v,
                geoid=v.geoid,
                simulation_state=simulation_state,
                environment=environment,
                target_soc=environment.config.dispatcher.ideal_fastcharge_soc_limit,
                charging_search_type=environment.config.dispatcher.charging_search_type,
            )
            is_charge_candidate = (
                environment.config.dispatcher.charging_range_km_threshold + nearest_station_distance
            ) >= range_remaining_km
            return is_charge_candidate

        low_soc_vehicles = simulation_state.get_vehicles(
            filter_function=charge_candidate,
        )

        # for each low_soc_vehicle that will conduct a refuel search, report the search event
        for v in low_soc_vehicles:
            report = instruction_generator_event_ops.refuel_search_event(
                v, simulation_state, environment
            )
            environment.reporter.file_report(report)

        charge_instructions = instruct_vehicles_to_dispatch_to_station(
            n=len(low_soc_vehicles),
            max_search_radius_km=self.config.max_search_radius_km,
            vehicles=low_soc_vehicles,
            simulation_state=simulation_state,
            environment=environment,
            target_soc=environment.config.dispatcher.ideal_fastcharge_soc_limit,
            charging_search_type=environment.config.dispatcher.charging_search_type,
        )

        return self, charge_instructions
