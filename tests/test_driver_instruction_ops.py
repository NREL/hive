
from unittest import TestCase

from hive.state.driver_state.driver_instruction_ops import human_go_home
from tests.mock_lobster import *


class TestDriverInstructionOps(TestCase):

    def test_human_go_home_with_enough_range(self):
        veh = mock_vehicle(soc=0.8, lat=0, lon=0)
        base = mock_base(lat=1, lon=1)              # 141-ish km away
        station = mock_station(lat=0.01, lon=0.01)  # 1.41km-ish away
        sim = mock_sim(vehicles=(veh,), bases=(base,), stations=(station,))
        env = mock_env()

        result = human_go_home(veh, base, sim, env)
        self.assertEqual(result, DispatchBaseInstruction(veh.id, base.id))

    def test_human_go_home_without_enough_range(self):
        veh = mock_vehicle(soc=0.05, lat=0, lon=0)
        base = mock_base(lat=1, lon=1)
        station = mock_station(lat=0.01, lon=0.01)
        sim = mock_sim(vehicles=(veh,), bases=(base,), stations=(station,))
        env = mock_env()

        result = human_go_home(veh, base, sim, env)
        self.assertEqual(result, DispatchStationInstruction(veh.id, station.id, mock_dcfc_charger_id()))
