from unittest import TestCase
from nrel.hive.dispatcher.instruction.instructions import (
    ChargeBaseInstruction,
    DispatchBaseInstruction,
    IdleInstruction,
    RepositionInstruction,
    ReserveBaseInstruction,
)
from nrel.hive.state.driver_state.human_driver_state.human_driver_state import (
    HumanAvailable,
    HumanUnavailable,
)
from nrel.hive.state.simulation_state import simulation_state_ops
from nrel.hive.state.vehicle_state.charging_station import ChargingStation
from nrel.hive.state.vehicle_state.idle import Idle
from nrel.hive.state.vehicle_state.reserve_base import ReserveBase

from nrel.hive.util.fp import throw_or_return
from nrel.hive.resources.mock_lobster import (
    DefaultIds,
    mock_base,
    mock_base_from_geoid,
    mock_dcfc_charger_id,
    mock_env,
    mock_human_driver,
    mock_request_from_geoids,
    mock_sim,
    mock_station,
    mock_station_from_geoid,
    mock_vehicle,
    mock_vehicle_from_geoid,
    somewhere,
    somewhere_else,
)


def on_schedule(a, b):
    return True


def off_schedule(a, b):
    return False


test_schedules = {"on": on_schedule, "off": off_schedule}


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

    def test_becomes_unavailable_while_station_charging(self):
        state = mock_human_driver(available=True, schedule_id="off", home_base_id="home_base")
        veh_id = DefaultIds.mock_vehicle_id()
        veh_state = ChargingStation.build(veh_id, "away_station", "DCFC")

        # vehicle is at away_station, but has a home_base with a home_station
        veh = mock_vehicle(
            lat=39.7664622,
            lon=-105.0390823,
            vehicle_id=veh_id,
            driver_state=state,
            vehicle_state=veh_state,
        )
        away_station = mock_station(lat=39.7664622, lon=-105.0390823, station_id="away_station")
        home_base = mock_base(
            lat=39.7544977,
            lon=-104.9809168,
            base_id="home_base",
            station_id="home_station",
        )
        home_station = mock_station(lat=39.7544977, lon=-104.9809168, station_id="home_station")

        sim = mock_sim(
            vehicles=(veh,),
            bases=(home_base,),
            stations=(home_station, away_station),
        )
        env = mock_env(schedules=test_schedules)
        error, updated_sim = state.update(sim, env)
        if error:
            raise error
        else:
            updated_veh = updated_sim.vehicles.get(veh_id)
            instruction = updated_veh.driver_state.generate_instruction(updated_sim, env, ())
            self.assertEqual(
                instruction,
                DispatchBaseInstruction("v0", "home_base"),
                "should have been sent home where charging is cheaper",
            )

    def test_becomes_unavailable_while_station_charging_no_home_charger(self):
        state = mock_human_driver(available=True, schedule_id="off", home_base_id="home_base")
        veh_id = DefaultIds.mock_vehicle_id()
        veh_state = ChargingStation.build(veh_id, "away_station", "DCFC")

        # vehicle is at away_station, but has a home_base with a home_station
        veh = mock_vehicle(
            lat=39.7664622,
            lon=-105.0390823,
            vehicle_id=veh_id,
            driver_state=state,
            vehicle_state=veh_state,
        )
        away_station = mock_station(lat=39.7664622, lon=-105.0390823, station_id="away_station")
        home_base = mock_base(
            lat=39.7544977,
            lon=-104.9809168,
            base_id="home_base",
            station_id=None,
        )

        sim = mock_sim(vehicles=(veh,), bases=(home_base,), stations=(away_station,))
        env = mock_env(schedules=test_schedules)
        error, updated_sim = state.update(sim, env)
        if error:
            raise error
        else:
            updated_veh = updated_sim.vehicles.get(veh_id)
            instruction = updated_veh.driver_state.generate_instruction(updated_sim, env, ())
            self.assertEqual(
                instruction,
                DispatchBaseInstruction("v0", "home_base"),
                "should have been sent home, " "enough charge to get to " "station in the morning",
            )

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
        veh = mock_vehicle_from_geoid(driver_state=state, geoid=somewhere(), soc=0.5)
        station = mock_station_from_geoid(geoid=somewhere())
        base = mock_base_from_geoid(station_id=station.id, geoid=somewhere())
        sim = mock_sim(vehicles=(veh,), bases=(base,), stations=(station,))
        env = mock_env()

        i = veh.driver_state.generate_instruction(sim, env)

        self.assertIsInstance(i, ChargeBaseInstruction)

    def test_reposition_instruction(self):
        # vehicle is at home but is available, should try to reposition
        state = mock_human_driver(available=True, schedule_id="on")
        veh = mock_vehicle(
            driver_state=state,
            vehicle_state=ReserveBase.build(
                DefaultIds.mock_vehicle_id(),
                DefaultIds.mock_base_id(),
            ),
        )
        req = mock_request_from_geoids(origin=somewhere_else(), destination=somewhere())
        sim = mock_sim(vehicles=(veh,))
        sim_w_req = throw_or_return(simulation_state_ops.add_request_safe(sim, req))
        env = mock_env()

        i = veh.driver_state.generate_instruction(sim_w_req, env)

        self.assertIsInstance(i, RepositionInstruction)

    def test_stop_fast_charging_instruction(self):
        state = mock_human_driver(available=True, schedule_id="on")
        veh = mock_vehicle(
            driver_state=state,
            vehicle_state=ChargingStation.build(
                vehicle_id=DefaultIds.mock_vehicle_id(),
                station_id=DefaultIds.mock_station_id(),
                charger_id=mock_dcfc_charger_id(),
            ),
            soc=0.9,
        )
        sim = mock_sim(vehicles=(veh,))
        env = mock_env()

        # the default soc limit for charging at a station is 0.8
        # so we should generate an idle instruction.
        i = veh.driver_state.generate_instruction(sim, env)

        self.assertIsInstance(i, IdleInstruction)

    def test_turn_off_at_home(self):
        state = mock_human_driver(available=False, schedule_id="off")
        veh = mock_vehicle_from_geoid(
            driver_state=state,
            vehicle_state=Idle.build(vehicle_id=DefaultIds.mock_vehicle_id()),
            geoid=somewhere(),
        )
        base = mock_base_from_geoid(geoid=somewhere())
        sim = mock_sim(vehicles=(veh,), bases=(base,))
        env = mock_env()

        # the driver is at home and idle so it should try to turn off
        # (i.e. transition to ReserveBase).
        i = veh.driver_state.generate_instruction(sim, env)

        self.assertIsInstance(i, ReserveBaseInstruction)
