from unittest import TestCase

from hive.runner import RunnerPayload
from tests.mock_lobster import *
from hive.state.simulation_state.update import Update


class TestUpdate(TestCase):

    def test_apply_update_with_user_provided_generator_update_function(self):
        """
        tests that a user can inject a function like `user_provided_update_fn` below and that it will
        be called when the simulation is stepped.

        this is validated by modifying a `stored_magic_number` attribute in the provided update fn,
        which itself ensures it is safely applied via an isinstace test.
        """

        old_magic_number = 7
        new_magic_number = 42

        class MockGenerator(NamedTuple, InstructionGenerator):
            stored_magic_number: int = old_magic_number

            def generate_instructions(self, simulation_state: SimulationState, envronment: Environment):
                return self, ()

        def user_provided_update_fn(instr_gen, sim):
            if isinstance(instr_gen, MockGenerator):
                return instr_gen._replace(stored_magic_number=new_magic_number)
            else:
                return None

        sim = mock_sim()
        env = mock_env()
        u = Update.build(mock_config().input, (MockGenerator(),), user_provided_update_fn)
        runner = RunnerPayload(sim, env, u)
        result, reports = u.apply_update(runner)
        updated_mock_gen = result.u.step_update.instruction_generators[0]
        self.assertEqual(updated_mock_gen.stored_magic_number, 42,
                         "the user provided update function should have been called")

    def test_apply_update_with_bogus_user_provided_generator_update_function(self):
        """
        a update function the user provides which produces an error should be reported
        """

        expected_error = RuntimeError("the owls are not what they seem")

        class MockGenerator(NamedTuple, InstructionGenerator):

            def generate_instructions(self, simulation_state: SimulationState, environment: Environment):
                return self, (), ()

        def user_provided_update_fn(instr_gen, sim):
            raise expected_error

        sim = mock_sim()
        env = mock_env()
        u = Update.build(mock_config().input, (MockGenerator(),), user_provided_update_fn)
        runner = RunnerPayload(sim, env, u)
        result, reports = u.apply_update(runner)

        self.assertEqual(len(reports), 1, "should have one report")
        self.assertEquals(reports[0]['report_type'], 'error', "should be an error")
        self.assertEquals(reports[0]['message'], repr(expected_error))
