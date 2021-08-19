from unittest import TestCase
from pathlib import Path
from pkg_resources import resource_filename

from hive.app import hive_cosim


class TestRunCosim(TestCase):

    def test_load_and_run_denver(self):
        # read scenario
        scenario_file = Path(resource_filename('hive.resources.scenarios.denver_downtown',
                                               'denver_demo.yaml'))
        rp0 = hive_cosim.load_scenario(scenario_file)
        time_steps = 5

        # crank 5 time steps
        crank_result_1 = hive_cosim.crank(rp0, time_steps=time_steps)
        expected_time = rp0.s.sim_time + (time_steps * rp0.s.sim_timestep_duration_seconds)
        self.assertEqual(crank_result_1.sim_time, expected_time, 'expected sim time is incorrect')

        # crank 5 more time steps
        crank_result_2 = hive_cosim.crank(crank_result_1.runner_payload, time_steps=time_steps)
        expected_time_2 = crank_result_1.runner_payload.s.sim_time + (time_steps * rp0.s.sim_timestep_duration_seconds)
        self.assertEqual(crank_result_2.sim_time, expected_time_2, 'expected sim time is incorrect')

        hive_cosim.close(crank_result_2.runner_payload)