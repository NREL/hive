import random
from typing import Tuple

from dataclasses import dataclass, replace

from tqdm import tqdm

from nrel.hive import package_root
from nrel.hive.dispatcher.instruction.instructions import IdleInstruction
from nrel.hive.dispatcher.instruction_generator.instruction_generator import (
    InstructionGenerator,
)
from nrel.hive.runner.runner_payload_ops import (
    get_instruction_generator,
    update_instruction_generator,
)
from nrel.hive.state.simulation_state.simulation_state import SimulationState
from nrel.hive.runner.environment import Environment
from nrel.hive.dispatcher.instruction.instruction import Instruction

import nrel.hive.app.hive_cosim as hc


@dataclass(frozen=True)
class CustomDispatcher(InstructionGenerator):
    random_instructions: int

    @classmethod
    def build(cls, random_instructions: int):
        return CustomDispatcher(random_instructions)

    def generate_instructions(
        self, simulation_state: SimulationState, environment: Environment
    ) -> Tuple[InstructionGenerator, Tuple[Instruction, ...]]:
        vehicles = simulation_state.get_vehicles()
        random_vehicles = random.choices(vehicles, k=self.random_instructions)
        instructions = []
        for vehicle in random_vehicles:
            instructions.append(IdleInstruction(vehicle.id))

        return (self, tuple(instructions))

    def new_random_state(self):
        new_r = random.choice(range(10))
        return replace(self, random_instructions=new_r)


def run():
    denver_demo_path = (
        package_root() / "resources" / "scenarios" / "denver_downtown" / "denver_demo.yaml"
    )

    dispatcher = CustomDispatcher.build(1)

    rp = hc.load_scenario(denver_demo_path, custom_instruction_generators=tuple([dispatcher]))

    for _ in tqdm(range(100)):
        # crank sim 10 time steps
        crank_result = hc.crank(rp, 10)

        # get dispatcher to update it
        dispatcher: CustomDispatcher = get_instruction_generator(
            crank_result.runner_payload, CustomDispatcher
        )

        # apply some change to the state of the dispatcher
        updated_dispatcher = dispatcher.new_random_state()

        # inject the dispatcher back into the simulation
        rp = update_instruction_generator(crank_result.runner_payload, updated_dispatcher)

    hc.close(rp)


if __name__ == "__main__":
    run()
