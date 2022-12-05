import functools as ft
from pathlib import Path
from typing import Iterable, Tuple, NamedTuple, Optional, TypeVar

import pandas as pd
from pandas import DataFrame
from tqdm import tqdm

from nrel.hive.dispatcher.instruction_generator.instruction_generator import InstructionGenerator
from nrel.hive.initialization.load import load_simulation, load_config
from nrel.hive.initialization.initialize_simulation import InitFunction
from nrel.hive.model.sim_time import SimTime
from nrel.hive.reporting.handler.vehicle_charge_events_handler import VehicleChargeEventsHandler
from nrel.hive.runner import RunnerPayload
from nrel.hive.util import SimulationStateError

T = TypeVar("T", bound=InstructionGenerator)


def load_scenario(
    scenario_file: Path,
    custom_instruction_generators: Optional[Tuple[T, ...]] = None,
    custom_init_functions: Optional[Iterable[InitFunction]] = None,
) -> RunnerPayload:
    """
    load a HIVE scenario from file and return the initial simulation state
    :param scenario_file: the HIVE scenario file to read
    :return: the initial simulation state payload
    :raises: Error when issues with files
    """
    config = load_config(scenario_file)
    initial_payload = load_simulation(config, custom_instruction_generators, custom_init_functions)

    # add a specialized Reporter handler that catches vehicle charge events
    initial_payload.e.reporter.add_handler(VehicleChargeEventsHandler())

    return initial_payload


class CrankResult(NamedTuple):
    runner_payload: RunnerPayload
    sim_time: SimTime
    charge_events: DataFrame


def crank(
    runner_payload: RunnerPayload,
    time_steps: int,
    progress_bar: bool = False,
    flush_events: bool = True,
) -> CrankResult:
    """
    advances the previous HIVE state some number of time steps
    :param runner_payload: the previous HIVE state
    :param time_steps: the number of steps to take, using the timestep size set in the HiveConfig
    :param progress_bar: show a progress bar in the console
    :param flush_events: write all requested event logs to their file destinations
    :return: the updated simulation state and all charge events that occurred
    """

    steps = tqdm(range(time_steps), position=0) if progress_bar else range(time_steps)

    def run_step(acc: Tuple[RunnerPayload, Tuple[DataFrame, ...]], i: int):
        rp0, events = acc
        # regular step
        rp1 = rp0.u.apply_update(rp0)
        if flush_events:
            rp1.e.reporter.flush(rp1)

        # output events
        new_events = None
        for handler in rp1.e.reporter.handlers:
            if isinstance(handler, VehicleChargeEventsHandler):
                new_events = handler.get_events()
                handler.clear()

        if new_events is None:
            raise SimulationStateError(
                f"VehicleChargeEventsHandler missing from reporter in env {rp1.e}"
            )

        updated_events = events + (new_events,)

        return rp1, updated_events

    initial = (runner_payload, ())
    next_state, unmerged_events = ft.reduce(run_step, steps, initial)
    events = pd.concat(unmerged_events)
    result = CrankResult(next_state, next_state.s.sim_time, events)
    return result


def close(runner_payload: RunnerPayload):
    """
    closes a hive simulation, finalizing all logging.
    does not need to be called, but, can only be called at most once
    as it will close file handlers.
    :param runner_payload: the final HIVE state to commit to logging
    """
    runner_payload.e.reporter.close(runner_payload)
    if runner_payload.e.config.global_config.write_outputs:
        runner_payload.e.config.to_yaml()
