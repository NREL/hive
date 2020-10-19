from unittest import TestCase

from tests.mock_lobster import *


def on_schedule(a, b):
    return True


def off_schedule(a, b):
    return False


test_schedules = {
    "on": on_schedule,
    "off": off_schedule
}


class TestHumanDriverState(TestCase):

    def test_stays_available(self):
        state = mock_human_driver(available=True, schedule_id="on")
        veh = mock_vehicle(driver_state=state)
        sim = mock_sim(vehicles=(veh,))

        env = mock_env(schedules=test_schedules)
        error, updated_sim = state.update(sim, env)
        if error:
            raise error
        else:
            veh_updated = updated_sim.vehicles.get(veh.id)
            self.assertIsInstance(veh_updated.driver_state, HumanAvailable)

    def test_becomes_unavailable(self):
        state = mock_human_driver(available=True, schedule_id="off")
        veh = mock_vehicle(driver_state=state)
        sim = mock_sim(vehicles=(veh,))

        env = mock_env(schedules=test_schedules)
        error, updated_sim = state.update(sim, env)
        if error:
            raise error
        else:
            veh_updated = updated_sim.vehicles.get(veh.id)
            self.assertIsInstance(veh_updated.driver_state, HumanUnavailable)

    def test_stays_unavailable(self):
        state = mock_human_driver(available=False, schedule_id="off")
        veh = mock_vehicle(driver_state=state)
        sim = mock_sim(vehicles=(veh,))

        env = mock_env(schedules=test_schedules)
        error, updated_sim = state.update(sim, env)
        if error:
            raise error
        else:
            veh_updated = updated_sim.vehicles.get(veh.id)
            self.assertIsInstance(veh_updated.driver_state, HumanUnavailable)

    def test_becomes_available(self):
        state = mock_human_driver(available=False, schedule_id="on")
        veh = mock_vehicle(driver_state=state)
        sim = mock_sim(vehicles=(veh,))

        env = mock_env(schedules=test_schedules)
        error, updated_sim = state.update(sim, env)
        if error:
            raise error
        else:
            veh_updated = updated_sim.vehicles.get(veh.id)
            self.assertIsInstance(veh_updated.driver_state, HumanAvailable)