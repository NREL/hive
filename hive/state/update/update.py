from __future__ import annotations

from typing import NamedTuple, Tuple

import functools as ft

from hive.runner import RunnerPayload
from hive.config import HiveConfig
from hive.dispatcher import DispatcherInterface, ManagedDispatcher
from hive.dispatcher.forecaster import BasicForecaster
from hive.dispatcher.manager import BasicManager
from hive.state.update import *
from pkg_resources import resource_filename


def _default_dispatcher(config: HiveConfig) -> DispatcherInterface:
    manager = BasicManager(demand_forecaster=BasicForecaster())
    dispatcher = ManagedDispatcher.build(
        manager=manager,
        geofence_file=config.io.geofence_file,
    )
    return dispatcher


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
        dispatcher = overriding_dispatcher if overriding_dispatcher else _default_dispatcher(config)

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

    def apply_update(self, runner_payload: RunnerPayload) -> RunnerPayload:
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

        # apply the simulation step using the StepSimulation update, which includes the dispatcher
        update_result, updated_step_fn = self.step_update.update(pre_step_result.runner_payload.s,
                                                                 pre_step_result.runner_payload.e)

        # resolve changes to Update
        next_update = Update(pre_step_result.updated_step_fns, updated_step_fn)

        return runner_payload._replace(
            s=update_result.simulation_state,
            u=next_update,
            r=runner_payload.r + update_result.reports
        )


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
    next_update_fns = p.updated_step_fns + (updated_fn,) if updated_fn else p.updated_step_fns + (fn,)
    updated_payload = p.runner_payload._replace(
        s=result.simulation_state,
        r=p.runner_payload.r + result.reports,
    )

    return p._replace(
        runner_payload=updated_payload,
        updated_step_fns=next_update_fns
    )
