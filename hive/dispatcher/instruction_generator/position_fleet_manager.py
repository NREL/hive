from __future__ import annotations

import random
from typing import Tuple, NamedTuple, TYPE_CHECKING

from h3 import h3

from hive.dispatcher.instruction_generator.instruction_generator_ops import (
    instruct_vehicles_to_reposition,
    instruct_vehicles_return_to_base,
)
from hive.dispatcher.instruction_generator.instruction_generator import InstructionGenerator
from hive.state.vehicle_state import *
from hive.util import Seconds, Kilometers

if TYPE_CHECKING:
    from hive.state.simulation_state.simulation_state import SimulationState
    from hive.model.roadnetwork.roadnetwork import RoadNetwork
    from hive.model.vehicle.vehicle import Vehicle
    from hive.dispatcher.forecaster.forecaster_interface import ForecasterInterface
    from hive.dispatcher.instruction.instruction_interface import Instruction
    from hive.util.typealiases import GeoId

random.seed(123)


class PositionFleetManager(NamedTuple, InstructionGenerator):
    """
    A class that determines where vehicles should be positioned.
    """
    demand_forecaster: ForecasterInterface
    update_interval_seconds: Seconds
    max_search_radius_km: Kilometers

    @staticmethod
    def _sample_random_location(road_network: RoadNetwork) -> GeoId:
        random_hex = random.choice(tuple(road_network.geofence.geofence_set))
        children = h3.h3_to_children(random_hex, road_network.sim_h3_resolution)
        return children.pop()

    def generate_instructions(
            self,
            simulation_state: SimulationState,
    ) -> Tuple[InstructionGenerator, Tuple[Instruction, ...]]:
        """
        Generate fleet targets for the dispatcher to execute based on the simulation state.

        :param simulation_state: The current simulation state

        :return: the updated PositionFleetManger along with instructions
        """

        def is_active(v: Vehicle) -> bool:
            return isinstance(v.vehicle_state, Idle) or \
                   isinstance(v.vehicle_state, Repositioning)

        def is_base_state(v: Vehicle) -> bool:
            return isinstance(v.vehicle_state, ChargingBase) or isinstance(v.vehicle_state, ReserveBase)

        # only generate instructions in 15 minute intervals
        if simulation_state.sim_time % self.update_interval_seconds != 0:
            return self, ()

        instructions = ()

        updated_forecaster, future_demand = self.demand_forecaster.generate_forecast(simulation_state)

        active_vehicles = simulation_state.get_vehicles(
            sort=True,
            sort_key=lambda v: v.energy_source.soc,
            filter_function=is_active,
        )

        n_active = len(active_vehicles)
        active_diff = n_active - future_demand.value

        if active_diff < 0:
            # we need abs(active_diff) more vehicles in service to meet demand
            base_vehicles = simulation_state.get_vehicles(
                sort=True,
                sort_key=lambda v: v.energy_source.soc,
                sort_reversed=True,
                filter_function=is_base_state,
            )
            repos_instructions = instruct_vehicles_to_reposition(abs(active_diff), base_vehicles, simulation_state)
            instructions = instructions + repos_instructions
        elif active_diff > 0:
            # we can remove active_diff vehicles from service
            base_instructions = instruct_vehicles_return_to_base(
                active_diff,
                self.max_search_radius_km,
                active_vehicles,
                simulation_state,
            )
            instructions = instructions + base_instructions

        return self._replace(demand_forecaster=updated_forecaster), instructions
