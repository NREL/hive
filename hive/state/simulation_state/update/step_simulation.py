from __future__ import annotations

import logging
import inspect
from typing import Tuple, Optional, NamedTuple, TYPE_CHECKING, Type, Union

import immutables

from returns.result import ResultE, Failure, Success
from hive.dispatcher.instruction.instruction import Instruction

from hive.dispatcher.instruction_generator.instruction_generator import (
    InstructionGenerator,
    InstructionGeneratorId,
)
from hive.dispatcher.instruction_generator.instruction_generator_ops import (
    generate_instructions,
)
from hive.state.simulation_state import simulation_state_ops
from hive.state.simulation_state.simulation_state import SimulationState
from hive.state.simulation_state.update.simulation_update import (
    SimulationUpdateFunction,
)
from hive.state.simulation_state.update.step_simulation_ops import (
    perform_vehicle_state_updates,
    apply_instructions,
    log_instructions,
    perform_driver_state_updates,
)
from hive.util.dict_ops import DictOps

if TYPE_CHECKING:
    from hive.runner.environment import Environment

log = logging.getLogger(__name__)


class StepSimulation(NamedTuple, SimulationUpdateFunction):
    instruction_generators: immutables.Map[InstructionGeneratorId, InstructionGenerator]
    instruction_generator_order: Tuple[InstructionGeneratorId, ...]

    @property
    def ordered_instruction_generators(self) -> Tuple[InstructionGenerator, ...]:
        instruction_generators = tuple(
            self.instruction_generators[ig_id]
            for ig_id in self.instruction_generator_order
        )
        return instruction_generators

    @classmethod
    def from_tuple(
        cls, instruction_generators: Tuple[InstructionGenerator, ...]
    ) -> StepSimulation:
        """
        Create a StepSimulation from a tuple of instruction generators.
        """
        return StepSimulation(
            instruction_generators=immutables.Map(
                {i_gen.name: i_gen for i_gen in instruction_generators}
            ),
            instruction_generator_order=tuple(
                i_gen.name for i_gen in instruction_generators
            ),
        )

    def update_instruction_generators(
        self, updated_i_gens: Tuple[InstructionGenerator, ...]
    ) -> StepSimulation:
        """
        Update the set of instruction generators.
        """
        return self._replace(
            instruction_generators=immutables.Map(
                {i_gen.name: i_gen for i_gen in updated_i_gens}
            ),
            instruction_generator_order=tuple(
                i_gen.name for i_gen in updated_i_gens
            ),
        )

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
        sim_with_drivers_updated = perform_driver_state_updates(simulation_state, env)

        i_stack, updated_i_gens = generate_instructions(
            self.ordered_instruction_generators, sim_with_drivers_updated, env
        )

        # pops the top instruction from the stack. this could be replaced with something like a priority queue
        final_instructions: Tuple[Instruction, ...] = ()
        for vid in i_stack.keys():
            i, _ = DictOps.pop_from_stack_dict(i_stack, vid)
            if not i:
                continue
            else:
                final_instructions = (i,) + final_instructions

        log_instructions(final_instructions, env, simulation_state.sim_time)

        # update drivers, update vehicles
        sim_with_instructions = apply_instructions(
            sim_with_drivers_updated, env, final_instructions
        )
        sim_vehicles_updated = perform_vehicle_state_updates(
            simulation_state=sim_with_instructions, env=env
        )

        # advance the simulation one time step
        sim_next_time_step = simulation_state_ops.tick(sim_vehicles_updated)

        updated_step_simulation = self.update_instruction_generators(updated_i_gens)
        return sim_next_time_step, updated_step_simulation

    def get_instruction_generator(
        self, identifier: Union[InstructionGeneratorId, Type[InstructionGenerator]]
    ) -> ResultE[InstructionGenerator]:
        """
        Get the instance of an internal instruction generator either by an id or the actual class type.
        """
        if isinstance(identifier, InstructionGeneratorId):
            i_gen = self.instruction_generators.get(identifier)
            if not i_gen:
                return Failure(
                    Exception(f"No instruction generator found with name {identifier}")
                )
            return Success(i_gen)
        elif inspect.isclass(identifier):
            for i_gen in self.instruction_generators.values():
                if isinstance(i_gen, identifier):
                    return Success(i_gen)
            return Failure(
                Exception(f"No instruction generator found with type {identifier}")
            )
        else:
            return Failure(Exception(f"Invalid identifier type {type(identifier)}"))

    def update_instruction_generator(
        self, i_gen: InstructionGenerator
    ) -> ResultE[StepSimulation]:
        """
        Update a single instruction generator.
        """
        identifier = i_gen.__class__.__name__
        if identifier not in self.instruction_generators.keys():
            return Failure(Exception(f"{identifier} not found in StepSimulation"))

        updated_instruction_generators = self.instruction_generators.set(
            identifier, i_gen
        )

        return Success(
            self._replace(instruction_generators=updated_instruction_generators)
        )
