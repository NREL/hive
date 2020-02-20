from __future__ import annotations

import functools as ft
from typing import NamedTuple, Tuple, TYPE_CHECKING

from hive.config import HiveConfig
from hive.dispatcher import DispatcherInterface
from hive.dispatcher import default_dispatcher
from hive.state.update.simulation_update import SimulationUpdateFunction
from hive.state.update.step_simulation import StepSimulation
from hive.state.update.charging_price_update import ChargingPriceUpdate
from hive.state.update.update_requests import UpdateRequests
from hive.state.update.cancel_requests import CancelRequests
from pkg_resources import resource_filename

if TYPE_CHECKING:
    from hive.runner import RunnerPayload


class UpdatePayload(NamedTuple):
    runner_payload: RunnerPayload
    updated_step_fns: Tuple[SimulationUpdateFunction, ...] = ()


class Update(NamedTuple):
    pre_step_update: Tuple[SimulationUpdateFunction, ...]
    step_update: StepSimulation

    @classmethod
    def build(cls,
              config: HiveConfig,
              overriding_dispatcher: DispatcherInterface = None) -> Update:
        """
        constructs the functionality to update the simulation each time step
        :param config: the scenario configuration
        :param overriding_dispatcher: any overriding dispatcher functionality
        :return: the Update that will be applied at each time step
        """
        dispatcher = overriding_dispatcher if overriding_dispatcher else default_dispatcher(config)

        requests_file = resource_filename("hive.resources.requests", config.io.requests_file)
        rate_structure_file = resource_filename("hive.resources.service_prices", config.io.rate_structure_file)
        charging_price_file = resource_filename("hive.resources.charging_prices", config.io.charging_price_file)

        # the basic, built-in set of updates which advance time of the supply and demand
        pre_step_update = (
            ChargingPriceUpdate.build(charging_price_file),
            UpdateRequests.build(requests_file, rate_structure_file),
            CancelRequests()
        )

        # add the dispatcher as a parameter of stepping the simulation state
        step_update = StepSimulation(dispatcher)

        # maybe in the future we also add a post_step_update set here too

        return Update(pre_step_update, step_update)

    def apply_update(self, runner_payload: RunnerPayload) -> [RunnerPayload, Tuple[str, ...]]:
        """
        applies the update at a time step, calling each SimulationUpdateFunction in order
        :param runner_payload: the current SimulationState and assets at the current simtime
        :return: the updated payload after one SimTime step
        """
        # run each pre_step_update
        pre_step_result = ft.reduce(
            _apply_fn,
            self.pre_step_update,
            UpdatePayload(runner_payload)
        )

        if isinstance(pre_step_result.runner_payload.s, Exception):
            raise pre_step_result.runner_payload.s

        # apply the simulation step using the StepSimulation update, which includes the dispatcher
        update_result, updated_step_fn = self.step_update.update(pre_step_result.runner_payload.s,
                                                                 pre_step_result.runner_payload.e)

        # resolve changes to Update
        next_update = Update(pre_step_result.updated_step_fns, updated_step_fn)

        updated_payload = runner_payload._replace(
            s=update_result.simulation_state,
            u=next_update
        )
        return updated_payload, update_result.reports


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

    if isinstance(result.simulation_state, Exception):
        raise result.simulation_state

    # if we received an updated version of this SimulationUpdateFunction, store it
    next_update_fns = p.updated_step_fns + (updated_fn,) if updated_fn else p.updated_step_fns + (fn,)
    updated_payload = p.runner_payload._replace(s=result.simulation_state)

    return p._replace(
        runner_payload=updated_payload,
        updated_step_fns=next_update_fns
    )
