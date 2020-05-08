from __future__ import annotations

from typing import Tuple, NamedTuple, TYPE_CHECKING

if TYPE_CHECKING:
    from hive.state.simulation_state.simulation_state import SimulationState
    from hive.runner.environment import Environment
    from hive.dispatcher.instruction.instruction import Instruction
    from hive.model.vehicle.vehicle import Vehicle
    from hive.config.dispatcher_config import DispatcherConfig

from hive.dispatcher.instruction_generator.instruction_generator import InstructionGenerator
from hive.dispatcher.instruction.instructions import DispatchTripInstruction
from hive.state.vehicle_state import Idle, Repositioning
from hive.util.helpers import H3Ops


class Dispatcher(NamedTuple, InstructionGenerator):
    """
    A managers algorithm that assigns vehicles greedily to most expensive request.
    """
    config: DispatcherConfig

    def generate_instructions(
            self,
            simulation_state: SimulationState,
            environment: Environment,
    ) -> Tuple[Dispatcher, Tuple[Instruction, ...]]:
        """
        Generate fleet targets for the dispatcher to execute based on the simulation state.

        :param simulation_state: The current simulation state

        :return: the updated Dispatcher along with instructions
        """
        # find requests that need a vehicle. Sorted by price high to low.
        # these instructions override fleet target instructions
        already_dispatched = []
        instructions = ()

        def _is_valid_for_dispatch(vehicle: Vehicle) -> bool:
            is_valid_state = isinstance(vehicle.vehicle_state, Idle) or \
                             isinstance(vehicle.vehicle_state, Repositioning)

            # TODO add remaining range to config
            mechatronics = environment.mechatronics.get(vehicle.mechatronics_id)
            range_remaining_km = mechatronics.range_remaining_km(vehicle)
            return bool(range_remaining_km > 20
                        and is_valid_state and vehicle.id not in already_dispatched)

        unassigned_requests = simulation_state.get_requests(
            sort=True,
            sort_key=lambda r: r.value,
            sort_reversed=True,
            filter_function=lambda r: not r.dispatched_vehicle
        )
        for request in unassigned_requests:
            nearest_vehicle = H3Ops.nearest_entity(geoid=request.origin,
                                                   entities=simulation_state.vehicles,
                                                   entity_search=simulation_state.v_search,
                                                   sim_h3_search_resolution=simulation_state.sim_h3_search_resolution,
                                                   is_valid=_is_valid_for_dispatch,
                                                   )
            if nearest_vehicle:
                instruction = DispatchTripInstruction(
                    vehicle_id=nearest_vehicle.id,
                    request_id=request.id,
                )

                already_dispatched.append(nearest_vehicle.id)

                instructions = instructions + (instruction,)

        return self, instructions
