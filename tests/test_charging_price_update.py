from unittest import TestCase, skip

from pkg_resources import resource_filename

from hive.state.update.charging_price_update import ChargingPriceUpdate
from tests.mock_lobster import *


class TestChargingPriceUpdate(TestCase):

    def test_charge_price_update_from_file(self):
        # prices are set to bump at 28800 (8 am)
        sim = mock_sim(stations=(mock_station("s1"), mock_station("s2"), mock_station("bs1"), ), sim_time=28801)
        s1, s2, bs1 = "s1", "s2", "bs1"  # StationIds in the Denver Downtown scenario
        file = resource_filename("hive.resources.scenarios.denver_downtown", "charging_prices_by_station_id.csv")
        fn = ChargingPriceUpdate.build(charging_file=file)
        result, _ = fn.update(sim)
        s1_prices = result.simulation_state.stations[s1].charger_prices
        s2_prices = result.simulation_state.stations[s2].charger_prices
        bs1_prices = result.simulation_state.stations[bs1].charger_prices
        self.assertEqual(s1_prices.get(Charger.DCFC), 0.05, "station s1 has a DCFC price of 0.05 per kw")
        self.assertEqual(s2_prices.get(Charger.DCFC), 0.05, "station s1 has a DCFC price of 0.05 per kw")
        self.assertEqual(bs1_prices.get(Charger.LEVEL_2), 0.005, "station s1 has a LEVEL_2 price of 0.05 per kw")

    def test_charge_price_default_price_is_zero(self):
        station = mock_station(chargers={
                Charger.LEVEL_1: 1,
                Charger.LEVEL_2: 1,
                Charger.DCFC: 1
        })
        sim = mock_sim(
            stations=(station, ),
            sim_time=1,
            sim_timestep_duration_seconds=1,
        )
        fn = ChargingPriceUpdate.build()
        result, _ = fn.update(sim)
        prices = result.simulation_state.stations[DefaultIds.mock_station_id()].charger_prices
        self.assertEqual(prices.get(Charger.LEVEL_1), 0.0, "LEVEL_1 charging should be free by default")
        self.assertEqual(prices.get(Charger.LEVEL_2), 0.0, "LEVEL_2 charging should be free by default")
        self.assertEqual(prices.get(Charger.DCFC), 0.0, "DCFC charging should be free by default")


    def test_charge_price_update_from_iterable(self):
        sim = mock_sim(
            stations=(mock_station(), ),
            sim_time=1,
            sim_timestep_duration_seconds=1,
        )
        env = mock_env()
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
        sim_ffwd = result1.simulation_state.step_simulation(env)
        result2,   _ = fn2.update(sim_ffwd)

        self.assertEqual(len(result1.reports), 0, "should have no errors")
        updated_price1 = result1.simulation_state.stations[DefaultIds.mock_station_id()].charger_prices[Charger.DCFC]
        updated_price2 = result2.simulation_state.stations[DefaultIds.mock_station_id()].charger_prices[Charger.DCFC]
        self.assertEqual(price1, updated_price1, "price should have been updated")
        self.assertEqual(price2, updated_price2, "price should have been updated")

    @skip
    def test_update(self):
        self.fail()
