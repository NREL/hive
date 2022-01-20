from unittest import TestCase

from hive.reporting import vehicle_event_ops
from hive.resources.mock_lobster import *


class TestStationLoadHandler(TestCase):
    def test_correctly_reads_one_vehicle_charge_event(self):
        """
        this test is mostly here just to make sure we don't mess with
        the structure of vehicle charge events in a way that would
        break station load reporting
        :return:
        """
        state = ChargingStation.build(vehicle_id=DefaultIds.mock_vehicle_id(),
                                      station_id=DefaultIds.mock_station_id(),
                                      charger_id=mock_dcfc_charger_id())
        veh = mock_vehicle(soc=0.1)
        sta = mock_station()
        sim = mock_sim(vehicles=(veh, ), stations=(sta, ))
        env = mock_env()
        mech = mock_bev()

        err, sim_charging = state.enter(sim, env)

        self.assertIsNone(err, "test invariant failed - vehicle in charging state")

        err, sim_charged = state.update(sim_charging, env)

        updated_vehicle = sim_charged.vehicles.get(DefaultIds.mock_vehicle_id())
        updated_station = sim_charged.stations.get(DefaultIds.mock_station_id())

        vehicle_charge_event = vehicle_event_ops.vehicle_charge_event(
            veh,
            updated_vehicle,
            sim_charged,
            updated_station,
            env.chargers.get(mock_dcfc_charger_id()),
            mech,
        )

        # perhaps in the future, add tests with multiple events
        vehicle_charge_events = (vehicle_charge_event, )

        result = vehicle_event_ops.construct_station_load_events(vehicle_charge_events, sim_charged)

        r = result[0]
        self.assertEqual(r.report['station_id'], DefaultIds.mock_station_id(),
                         "should have captured which station this happened at")
        self.assertGreater(r.report['energy'], 0.0,
                           "we should have captured the effect of 60 seconds of charge time")
