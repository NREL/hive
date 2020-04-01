from __future__ import annotations

import random
from typing import Tuple, NamedTuple, TYPE_CHECKING

from h3 import h3

from hive.dispatcher.managers.manager_interface import ManagerInterface
from hive.dispatcher.instruction.instructions import RepositionInstruction, DispatchBaseInstruction
from hive.state.vehicle_state import *
from hive.util import Seconds
from hive.util.helpers import H3Ops

if TYPE_CHECKING:
    from hive.state.simulation_state.simulation_state import SimulationState
    from hive.model.roadnetwork.roadnetwork import RoadNetwork
    from hive.dispatcher.forecaster.forecaster_interface import ForecasterInterface
    from hive.dispatcher.instruction.instruction_interface import Instruction
    from hive.util.typealiases import Report, GeoId, SimTime

random.seed(123)


class FleetPosition(NamedTuple, ManagerInterface):
    """
    A class that determines where vehicles should be positioned.
    """
    demand_forecaster: ForecasterInterface
    update_interval_seconds: Seconds

    @staticmethod
    def _sample_random_location(road_network: RoadNetwork) -> GeoId:
        random_hex = random.choice(tuple(road_network.geofence.geofence_set))
        children = h3.h3_to_children(random_hex, road_network.sim_h3_resolution)
        return children.pop()

    def generate_instructions(
            self,
            simulation_state: SimulationState,
    ) -> Tuple[ManagerInterface, Tuple[Instruction, ...], Tuple[Report, ...]]:
        """
        Generate fleet targets for the dispatcher to execute based on the simulation state.

        :param simulation_state: The current simulation state

        :return: the updated Manager along with instructions and reports
        """

        def is_active(vstate: VehicleState) -> bool:
            return not isinstance(vstate, DispatchBase) \
                   and not isinstance(vstate, ChargingBase) \
                   and not isinstance(vstate, ReserveBase) \
                   and not isinstance(vstate, OutOfService)

        def is_base_state(vstate: VehicleState) -> bool:
            return isinstance(vstate, ChargingBase) or isinstance(vstate, ReserveBase)

        def is_non_interrupt_state(vstate: VehicleState) -> bool:
            return isinstance(vstate, DispatchStation) \
                   or isinstance(vstate, ChargingStation) \
                   or isinstance(vstate, ServicingTrip)

        # only generate instructions in 15 minute intervals
        if simulation_state.sim_time % self.update_interval_seconds != 0:
            return self, (), ()

        instructions = ()

        updated_forecaster, future_demand = self.demand_forecaster.generate_forecast(simulation_state)

        active_vehicles = [v for v in simulation_state.vehicles.values()
                           if is_active(v.vehicle_state)]
        n_active = len(active_vehicles)
        active_diff = n_active - future_demand.value

        if active_diff < 0:
            # we need abs(active_diff) more vehicles in service to meet demand
            base_vehicles = [v for v in simulation_state.vehicles.values() if is_base_state(v.vehicle_state)]
            for i, veh in enumerate(base_vehicles):
                if i + 1 > abs(active_diff):
                    break
                random_location = self._sample_random_location(simulation_state.road_network)
                instruction = RepositionInstruction(vehicle_id=veh.id, destination=random_location)
                instructions = instructions + (instruction, )

        elif active_diff > 0:
            # we can remove active_diff vehicles from service
            for i, veh in enumerate(active_vehicles):
                if i + 1 > active_diff:
                    break
                elif is_non_interrupt_state(veh.vehicle_state):
                    continue

                nearest_base = H3Ops.nearest_entity(geoid=veh.geoid,
                                                    entities=simulation_state.bases,
                                                    entity_search=simulation_state.b_search,
                                                    sim_h3_search_resolution=simulation_state.sim_h3_search_resolution)
                if nearest_base:
                    instruction = DispatchBaseInstruction(
                        vehicle_id=veh.id,
                        base_id=nearest_base.id,
                    )

                    instructions = instructions + (instruction, )
                else:
                    # user set the max search radius too low
                    continue

        return self._replace(demand_forecaster=updated_forecaster), instructions, ()

