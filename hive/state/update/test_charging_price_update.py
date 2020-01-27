from unittest import TestCase

from hive.state.update.charging_price_update import ChargingPriceUpdate
from tests.mock_lobster import *


class TestChargingPriceUpdate(TestCase):
    def test_charge_price_update_from_file(self):
        self.fail()

    def test_charge_price_update_from_iterable(self):
        sim = mock_sim(
            stations=(mock_station(), ),
            sim_time=1,
            sim_timestep_duration_seconds=1,
        )
        price1, price2 = 0.03, 0.05
        update = iter([
            {"time": "0", "station_id": "default", "charger_type": "DCFC", "price_kw": str(price1)},
            {"time": "1", "station_id": "default", "charger_type": "DCFC", "price_kw": "1234.5678"},
            {"time": "1", "station_id": "default", "charger_type": "DCFC", "price_kw": str(price2)},
            {"time": "2", "station_id": "default", "charger_type": "DCFC", "price_kw": "-765.4321"},
        ])
        fn1 = ChargingPriceUpdate.build(default_values=update)

        # the first update should pull in the first row of data;
        # the second update should pull in the second and third row
        # the fourth row should not have been read
        result1, fn2 = fn1.update(sim)
        sim_ffwd = result1.simulation_state.step_simulation()
        result2,   _ = fn2.update(sim_ffwd)

        self.assertEqual(len(result1.reports), 0, "should have no errors")
        updated_price1 = result1.simulation_state.stations[DefaultIds.mock_station_id()].charger_prices[Charger.DCFC]
        updated_price2 = result2.simulation_state.stations[DefaultIds.mock_station_id()].charger_prices[Charger.DCFC]
        self.assertEqual(price1, updated_price1, "price should have been updated")
        self.assertEqual(price2, updated_price2, "price should have been updated")

    def test_update(self):
        self.fail()
