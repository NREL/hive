from __future__ import annotations

import functools as ft
from typing import NamedTuple, Tuple, TYPE_CHECKING, Callable, Optional

import immutables

from hive.config import HiveConfig
from hive.dispatcher.instruction_generator.instruction_generator import (
    InstructionGenerator,
)
from hive.state.simulation_state.simulation_state import SimulationState
from hive.state.simulation_state.update.cancel_requests import CancelRequests
from hive.state.simulation_state.update.charging_price_update import ChargingPriceUpdate
from hive.state.simulation_state.update.simulation_update import (
    SimulationUpdateFunction,
)
from hive.state.simulation_state.update.step_simulation import StepSimulation
from hive.state.simulation_state.update.update_requests_from_file import (
    UpdateRequestsFromFile,
)

if TYPE_CHECKING:
    from hive.runner import RunnerPayload


class UpdatePayload(NamedTuple):
    runner_payload: RunnerPayload
    updated_step_fns: Tuple[SimulationUpdateFunction, ...] = ()


class Update(NamedTuple):
    pre_step_update: Tuple[SimulationUpdateFunction, ...]
    step_update: StepSimulation

    @classmethod
    def build(
        cls,
        config: HiveConfig,
        instruction_generators: Tuple[InstructionGenerator, ...],
    ) -> Update:
        """
        constructs the functionality to update the simulation each time step

        :param config:
        :param instruction_generators: any overriding dispatcher functionality
        :return: the Update that will be applied at each time step
        """

        # the basic, built-in set of updates which advance time of the supply and demand
        pre_step_update = (
            ChargingPriceUpdate.build(
                config.input_config.charging_price_file,
                config.input_config.chargers_file,
                lazy_file_reading=config.global_config.lazy_file_reading,
            ),
            UpdateRequestsFromFile.build(
                config.input_config.requests_file,
                config.input_config.rate_structure_file,
                lazy_file_reading=config.global_config.lazy_file_reading,
            ),
            CancelRequests(),
        )

        # add the dispatcher as a parameter of stepping the simulation state
        step_update = StepSimulation.from_tuple(instruction_generators)

        # maybe in the future we also add a post_step_update set here too

        return Update(pre_step_update, step_update)

    def apply_update(self, runner_payload: RunnerPayload) -> RunnerPayload:
        """
        applies the update at a time step, calling each SimulationUpdateFunction in order

        :param runner_payload: the current SimulationState and assets at the current simtime
        :return: the updated payload after one SimTime step
        """

        # clear the cache of applied instructions from the SimulationState
        init_rp = runner_payload._replace(
            s=runner_payload.s._replace(applied_instructions=immutables.Map())
        )

        # run each pre_step_update
        pre_step_result = ft.reduce(
            _apply_fn, self.pre_step_update, UpdatePayload(init_rp)
        )

        # apply the simulation step using the StepSimulation update, which includes the dispatcher
        updated_sim, updated_step_fn = self.step_update.update(
            pre_step_result.runner_payload.s, pre_step_result.runner_payload.e
        )

        # resolve changes to Update
        next_update = Update(pre_step_result.updated_step_fns, updated_step_fn)

        updated_payload = runner_payload._replace(s=updated_sim, u=next_update)

        return updated_payload


def _apply_fn(p: UpdatePayload, fn: SimulationUpdateFunction) -> UpdatePayload:
    """
    applies an update function to this payload. if the update function
    was also updated, then store the updated version of the update function
    invariant: the update functions (self.u) were emptied before applying these
    (we don't want to duplicate them!)

    :param fn: an update function
    :param sim: the current state of the simulation
    :param env: the simulation environment
    :return: the updated payload, with update function applied to the simulation,
    and the update function possibly updated itself
    """
    result, updated_fn = fn.update(p.runner_payload.s, p.runner_payload.e)

    # if we received an updated version of this SimulationUpdateFunction, store it
    next_update_fns = (
        p.updated_step_fns + (updated_fn,) if updated_fn else p.updated_step_fns + (fn,)
    )
    updated_payload = p.runner_payload._replace(s=result)

    return p._replace(
        runner_payload=updated_payload,
        updated_step_fns=next_update_fns,
    )
