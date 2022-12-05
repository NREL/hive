from __future__ import annotations

import argparse
import logging
from typing import Dict

import ray
from ray import tune

from nrel.hive.initialization.load import load_simulation, load_config
from nrel.hive.reporting.reporter import Reporter
from nrel.hive.runner.local_simulation_runner import LocalSimulationRunner
from nrel.hive.runner.runner_payload import RunnerPayload

parser = argparse.ArgumentParser(description="run hive")
parser.add_argument(
    "scenario_file",
    help='which scenario file to run (try "denver_downtown.yaml" or "manhattan.yaml")',
)

log = logging.getLogger("hive")


class DummyReporter(Reporter):
    """
    dummy reporter that does nothing
    """

    def log_sim_state(self, sim_state):
        pass

    def sim_report(self, report):
        pass

    def close(self):
        pass


class OptimizationWrapper(tune.Trainable):
    """
    wrapper for a tune optimization.
    """

    @staticmethod
    def _scoring_function(payload: RunnerPayload) -> float:
        score = sum([v.balance for v in payload.s.vehicles.values()])
        print("SCORE ", score)
        print("VEHICLES ", payload.s.vehicles.values())
        return score

    def _setup(self, d: Dict[str, int]):
        scenarios = {
            1: "denver_demo.yaml",
            2: "denver_demo_constrained_charging.yaml",
        }
        scenario_file = scenarios[d["scenario"]]
        log.info(f"setting up experiment with scenario {scenario_file}")

        config = load_config(scenario_file)
        rp = load_simulation(config)

        self.initial_payload = rp

    def _train(self) -> Dict[str, float]:
        sim_result = LocalSimulationRunner.run(self.initial_payload)
        score = self._scoring_function(sim_result)

        return {"score": score}


def run() -> int:
    """
    entry point for a hive application run
    :return: 0 if success, 1 if error
    """
    ray.init(local_mode=True)

    _welcome_to_hive()

    log.info("running tune experiments")

    result = tune.run(
        OptimizationWrapper,
        stop={"training_iteration": 1},
        config={"scenario": tune.grid_search([1, 2])},
    )

    df = result.dataframe()
    df = df[["config/scenario", "score"]]

    df.to_csv("results.csv", index=False)

    return 0


def _welcome_to_hive():
    welcome = """
##     ##  ####  ##     ##  #######
##     ##   ##   ##     ##  ##
#########   ##   ##     ##  ######
##     ##   ##    ##   ##   ##
##     ##  ####     ###     #######

                .' '.            __
       .        .   .           (__\_
        .         .         . -{{_(|8)
          ' .  . ' ' .  . '     (__/
    """

    log.info(welcome)


if __name__ == "__main__":
    run()
