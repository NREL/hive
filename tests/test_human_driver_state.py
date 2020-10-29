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

    def test_go_home_instruction(self):
        # vehicle and base/station are at different locations
        state = mock_human_driver(available=False, schedule_id="off")
        veh = mock_vehicle_from_geoid(driver_state=state, geoid=somewhere())
        station = mock_station_from_geoid(geoid=somewhere_else())
        base = mock_base_from_geoid(station_id=station.id, geoid=somewhere_else())
        sim = mock_sim(vehicles=(veh,), bases=(base,), stations=(station,))
        env = mock_env()

        i = veh.driver_state.generate_instruction(sim, env)

        self.assertIsInstance(i, DispatchBaseInstruction)

    def test_home_charge_instruction(self):
        # vehicle and base/station are at same location (i.e. vehicle is at home)
        state = mock_human_driver(available=False, schedule_id="off")
        veh = mock_vehicle_from_geoid(driver_state=state, geoid=somewhere())
        station = mock_station_from_geoid(geoid=somewhere())
        base = mock_base_from_geoid(station_id=station.id, geoid=somewhere())
        sim = mock_sim(vehicles=(veh,), bases=(base,), stations=(station,))
        env = mock_env()

        i = veh.driver_state.generate_instruction(sim, env)

        self.assertIsInstance(i, ChargeBaseInstruction)

    def test_reposition_instruction(self):
        # vehicle is at home but is available, should try to reposition
        state = mock_human_driver(available=True, schedule_id="on")
        veh = mock_vehicle(driver_state=state, vehicle_state=ReserveBase(
            DefaultIds.mock_vehicle_id(),
            DefaultIds.mock_base_id(),
        ))
        req = mock_request_from_geoids(origin=somewhere_else(), destination=somewhere())
        sim = mock_sim(vehicles=(veh,))
        _, sim_w_req = simulation_state_ops.add_request(sim, req)
        env = mock_env()

        i = veh.driver_state.generate_instruction(sim_w_req, env)

        self.assertIsInstance(i, RepositionInstruction)


