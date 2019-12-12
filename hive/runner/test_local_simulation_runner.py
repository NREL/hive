from unittest import TestCase

from hive.runner.run_config import RunConfig, Sim


class TestLocalSimulationRunner(TestCase):

    def test_run(self):
        self.fail()


class TestLocalSimulationRunnerAssets:

    @classmethod
    def mock_config(cls) -> RunConfig:
        return RunConfig(sim=Sim(), )
