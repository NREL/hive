from __future__ import annotations

from hive.dispatcher import Dispatcher
from hive.state import simulation_state_ops
from hive.state.simulation_state import SimulationState


def step(simulation_state: SimulationState, dispatcher: Dispatcher) -> SimulationState:
    """
    take one step in the simulation
    :return: simulation at time t+1
    """
    instructions = dispatcher.generate_instructions(simulation_state)
    sim_with_instructions = simulation_state_ops.apply_instructions(simulation_state, instructions)
    sim_next_time_step = sim_with_instructions.step_simulation()
    return sim_next_time_step
