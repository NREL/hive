from unittest import TestCase

from hive.model.instruction import *
from tests.mock_lobster import *
from hive.state.simulation_state.update.step_simulation import step_simulation


class TestInstructions(TestCase):

    def test_set_vehicle_intention_charge(self):
        somewhere = h3.geo_to_h3(39.7539, -104.974, 15)
        somewhere_else = h3.geo_to_h3(39.755, -104.976, 15)
        sta = mock_station_from_geoid(geoid=somewhere)
        veh = mock_vehicle_from_geoid(geoid=somewhere, soc=0.2)
        sim = mock_sim().add_vehicle(veh).add_station(sta)
        env = mock_env()

        instruction = ChargeStationInstruction(
            vehicle_id=veh.id,
            station_id=sta.id,
            charger=Charger.DCFC
        )
        sim_update_error, sim_updated = instruction.apply_instruction(sim, env)
        if sim_update_error:
            self.fail(sim_update_error)
        sim_stepped = step_simulation(sim_updated, env)

        # The station only has 1 DCFC charger
        updated_station = sim_stepped.stations[sta.id]
        self.assertEqual(updated_station.has_available_charger(Charger.DCFC), False)

        new_instruction = RepositionInstruction(
            vehicle_id=veh.id,
            destination=somewhere_else,
        )

        sim_interrupt_error, sim_interrupt_charge = new_instruction.apply_instruction(sim_stepped, env)
        if sim_interrupt_error:
            self.fail(sim_interrupt_error.args)

        sim_stepped_again = step_simulation(sim_interrupt_charge, env)

        self.assertIsNotNone(sim_stepped_again)

        updated_station = sim_stepped_again.stations[sta.id]
        self.assertEqual(updated_station.has_available_charger(Charger.DCFC), True)

