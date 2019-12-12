from __future__ import annotations

from typing import Tuple

from hive.dispatcher import Dispatcher
from hive.dispatcher.instruction import Instruction
from hive.state import simulation_state_ops
from hive.state.simulation_state import SimulationState


def step(simulation_state: SimulationState, dispatcher: Dispatcher) -> Tuple[SimulationState, Dispatcher, Tuple[Instruction, ...]]:
    """
    take one step in the simulation
    :return: simulation at time t+1
    """
    updated_dispatcher, instructions = dispatcher.generate_instructions(simulation_state)
    sim_with_instructions = simulation_state_ops.apply_instructions(simulation_state, instructions)
    sim_next_time_step = sim_with_instructions.step_simulation()
    return sim_next_time_step, updated_dispatcher, instructions
