from unittest import TestCase, skip

from hive.state.simulation_state.update.charging_price_update import ChargingPriceUpdate
from hive.state.simulation_state.update.step_simulation_ops import perform_vehicle_state_updates
from tests.mock_lobster import *


class TestChargingPriceUpdate(TestCase):

    def test_charge_price_update_from_station_id_file(self):
        # prices are set to bump at 28800 (8 am)
        sim = mock_sim(
            stations=(
                mock_station_from_geoid("s1", '8f268cdac268430'),
                mock_station_from_geoid("s2", '8f268cdac268589'),
                mock_station_from_geoid("bs1", '8f268cdac268433')),
            sim_time=28801)
        env = mock_env()
        s1, s2, bs1 = "s1", "s2", "bs1"  # StationIds in the Denver Downtown scenario
        file = resource_filename("hive.resources.scenarios.denver_downtown.charging_prices", "denver_charging_prices_by_station_id.csv")
        fn = ChargingPriceUpdate.build(file, env.config.input_config.chargers_file)
        result, _ = fn.update(sim, env)
        s1_prices = result.simulation_state.stations[s1].charger_prices_per_kwh
        s2_prices = result.simulation_state.stations[s2].charger_prices_per_kwh
        bs1_prices = result.simulation_state.stations[bs1].charger_prices_per_kwh
        self.assertEqual(s1_prices.get(mock_dcfc_charger_id()), 0.5, "station s1 has a DCFC price of 0.5 per kwh")
        self.assertEqual(s2_prices.get(mock_dcfc_charger_id()), 0.5, "station s1 has a DCFC price of 0.5 per kwh")
        self.assertEqual(bs1_prices.get(mock_l2_charger_id()), 0.05, "station s1 has a LEVEL_2 price of 0.05 per kwh")
        fn.reader.close()

    def test_charge_price_update_from_geoid_file(self):
        # prices are set to bump at 28800 (8 am)
        stations = (
            mock_station("s1", 39.752233, -104.976061, chargers=immutables.Map({mock_dcfc_charger_id(): 10})),
            mock_station("s2", 39.759521,-104.97526, chargers=immutables.Map({mock_dcfc_charger_id(): 10})),
            mock_station("bs1", 39.754695,-104.988116, chargers=immutables.Map({mock_l2_charger_id(): 10})),
        )
        sim = mock_sim(stations=stations, sim_time=36001)
        env = mock_env()
        s1, s2, bs1 = "s1", "s2", "bs1"  # StationIds in the Denver Downtown scenario
        file = resource_filename("hive.resources.scenarios.denver_downtown.charging_prices", "denver_charging_prices_by_geoid.csv")
        fn = ChargingPriceUpdate.build(file, env.config.input_config.chargers_file)
        result, _ = fn.update(sim, env)
        s1_prices = result.simulation_state.stations[s1].charger_prices_per_kwh
        s2_prices = result.simulation_state.stations[s2].charger_prices_per_kwh
        bs1_prices = result.simulation_state.stations[bs1].charger_prices_per_kwh
        self.assertEqual(s1_prices.get(mock_dcfc_charger_id()), 0.3, "station s1 has a DCFC price of 0.3 per kwh")
        self.assertEqual(s2_prices.get(mock_dcfc_charger_id()), 0.3, "station s1 has a DCFC price of 0.3 per kwh")
        self.assertEqual(bs1_prices.get(mock_l2_charger_id()), 0.03, "station s1 has a LEVEL_2 price of 0.03 per kwh")
        fn.reader.close()

    def test_charge_price_default_price_is_zero(self):
        station = mock_station(chargers=immutables.Map({
                mock_l1_charger_id(): 1,
                mock_l2_charger_id(): 1,
                mock_dcfc_charger_id(): 1
        }))
        sim = mock_sim(
            stations=(station, ),
            sim_time=1,
            sim_timestep_duration_seconds=1,
        )
        env = mock_env()
        fn = ChargingPriceUpdate.build(None, env.config.input_config.chargers_file)
        result, _ = fn.update(sim, env)
        prices = result.simulation_state.stations[DefaultIds.mock_station_id()].charger_prices_per_kwh
        self.assertEqual(prices.get(mock_l1_charger_id()), 0.0, "LEVEL_1 charging should be free by default")
        self.assertEqual(prices.get(mock_l2_charger_id()), 0.0, "LEVEL_2 charging should be free by default")
        self.assertEqual(prices.get(mock_dcfc_charger_id()), 0.0, "DCFC charging should be free by default")

    @skip
    def test_charge_price_update_from_iterable(self):
        # I'm not sure this is testing any real functionality since we only want this for writing
        # the default values
        sim = mock_sim(
            stations=(mock_station(), ),
            sim_time=1,
            sim_timestep_duration_seconds=1,
        )
        env = mock_env()
        price1, price2 = 0.03, 0.05
        update = iter([
            {"time": "0", "station_id": "default", "charger_type": mock_dcfc_charger_id(), "price_kwh": str(price1)},
            {"time": "1", "station_id": "default", "charger_type": mock_dcfc_charger_id(), "price_kwh": "1234.5678"},
            {"time": "1", "station_id": "default", "charger_type": mock_dcfc_charger_id(), "price_kwh": str(price2)},
            {"time": "2", "station_id": "default", "charger_type": mock_dcfc_charger_id(), "price_kwh": "-765.4321"},
        ])
        fn1 = ChargingPriceUpdate.build(fallback_values=update)

        # the first update should pull in the first row of data;
        # the second update should pull in the second and third row
        # the fourth row should not have been read
        result1, fn2 = fn1.update(sim, env)
        sim_ffwd = perform_vehicle_state_updates(result1.simulation_state, env)
        result2, fn3 = fn2.update(sim_ffwd, env)

        self.assertEqual(len(result1.reports), 0, "should have no errors")
        updated_price1 = result1.simulation_state.stations[DefaultIds.mock_station_id()].charger_prices_per_kwh[mock_dcfc_charger_id()]
        updated_price2 = result2.simulation_state.stations[DefaultIds.mock_station_id()].charger_prices_per_kwh[mock_dcfc_charger_id()]
        self.assertEqual(price1, updated_price1, "price should have been updated")
        self.assertEqual(price2, updated_price2, "price should have been updated")

