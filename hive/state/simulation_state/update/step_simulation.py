from __future__ import annotations

import functools as ft
import logging
from typing import Tuple, Optional, NamedTuple, TYPE_CHECKING, Callable

from hive.dispatcher.instruction_generator.instruction_generator import InstructionGenerator
from hive.dispatcher.instruction_generator.instruction_generator_ops import generate_instructions
from hive.state.simulation_state import simulation_state_ops
from hive.state.simulation_state.simulation_state import SimulationState
from hive.state.simulation_state.update.simulation_update import SimulationUpdateFunction
from hive.state.simulation_state.update.step_simulation_ops import (
    perform_vehicle_state_updates,
    apply_instructions,
    log_instructions,
    instruction_generator_update_fn,
    UserProvidedUpdateAccumulator,
    perform_driver_state_updates,
)

if TYPE_CHECKING:
    from hive.runner.environment import Environment

log = logging.getLogger(__name__)


class StepSimulation(NamedTuple, SimulationUpdateFunction):
    instruction_generators: Tuple[InstructionGenerator, ...]
    instruction_generator_update_fn: Callable[
        [InstructionGenerator, SimulationState], Optional[InstructionGenerator]] = lambda a, b: None

    def update(
            self,
            simulation_state: SimulationState,
            env: Environment,
    ) -> Tuple[SimulationState, Optional[StepSimulation]]:
        """
        generates all instructions for this time step and then attempts to apply them to the SimulationState
        upon completion, returns the modified simulation state along with any reports and additionally, returns
        an updated version of the StepSimulation (in the case of any modifications to the InstructionGenerators)

        before beginning, it first calls a provided update function on the set of InstructionGenerators for any
        control models injected by the user

        :param simulation_state: state to modify
        :param env: the sim environment
        :return: updated simulation state, with reports, along with the (optionally) updated StepSimulation
        """
        # allow the user to inject changes to the InstructionGenerators
        user_update_result = ft.reduce(
            instruction_generator_update_fn(self.instruction_generator_update_fn, simulation_state),
            self.instruction_generators,
            UserProvidedUpdateAccumulator()
        )

        # TODO: I refactored the UserProvidedUpdateAccumulator to raise any errors due to a problem I had where it
        #  was failing silently. Once we decide on our error handling strategy we should revisit this. -NR

        instr_result = generate_instructions(user_update_result.updated_fns, simulation_state, env)
        log_instructions(instr_result.sim, env)

        # update drivers, update vehicles
        sim_with_drivers_updated = perform_driver_state_updates(instr_result.sim, env)
        sim_with_instructions = apply_instructions(sim_with_drivers_updated, env)
        sim_vehicles_updated = perform_vehicle_state_updates(simulation_state=sim_with_instructions, env=env)

        # advance the simulation one time step
        sim_next_time_step = simulation_state_ops.tick(sim_vehicles_updated)

        updated_step_simulation = self._replace(instruction_generators=instr_result.updated_instruction_generators)
        return sim_next_time_step, updated_step_simulation
