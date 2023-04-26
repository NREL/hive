from unittest import TestCase
import immutables

from pkg_resources import resource_filename
from nrel.hive.resources.mock_lobster import (
    mock_dcfc_charger_id,
    mock_env,
    mock_l1_charger_id,
    mock_l2_charger_id,
    mock_sim,
    mock_station,
    mock_station_from_geoid,
)

from nrel.hive.state.simulation_state.update.charging_price_update import ChargingPriceUpdate


class TestChargingPriceUpdate(TestCase):
    def test_charge_price_update_from_station_id_file(self):
        # prices are set to bump at 28800 (8 am)
        sim = mock_sim(
            stations=(
                mock_station_from_geoid("s1", "8f268cdac268430"),
                mock_station_from_geoid("s2", "8f268cdac268589"),
                mock_station_from_geoid("bs1", "8f268cdac268433"),
            ),
            sim_time=28801,
        )
        env = mock_env()
        s1, s2, bs1 = (
            "s1",
            "s2",
            "bs1",
        )  # StationIds in the Denver Downtown scenario
        file = resource_filename(
            "nrel.hive.resources.scenarios.denver_downtown.charging_prices",
            "denver_charging_prices_by_station_id.csv",
        )
        fn = ChargingPriceUpdate.build(file, env.config.input_config.chargers_file)
        result, _ = fn.update(sim, env)
        s1_prices = {c_id: cs.price_per_kwh for c_id, cs in result.stations[s1].state.items()}
        s2_prices = {c_id: cs.price_per_kwh for c_id, cs in result.stations[s2].state.items()}
        bs1_prices = {c_id: cs.price_per_kwh for c_id, cs in result.stations[bs1].state.items()}
        self.assertEqual(
            s1_prices.get(mock_dcfc_charger_id()),
            0.5,
            "station s1 has a DCFC price of 0.5 per kwh",
        )
        self.assertEqual(
            s2_prices.get(mock_dcfc_charger_id()),
            0.5,
            "station s1 has a DCFC price of 0.5 per kwh",
        )
        self.assertEqual(
            bs1_prices.get(mock_l2_charger_id()),
            0.05,
            "station s1 has a LEVEL_2 price of 0.05 per kwh",
        )
        fn.reader.close()

    def test_charge_price_update_from_geoid_file(self):
        # prices are set to bump at 28800 (8 am)
        stations = (
            mock_station(
                "s1",
                39.752233,
                -104.976061,
                chargers=immutables.Map({mock_dcfc_charger_id(): 10}),
            ),
            mock_station(
                "s2",
                39.759521,
                -104.97526,
                chargers=immutables.Map({mock_dcfc_charger_id(): 10}),
            ),
            mock_station(
                "bs1",
                39.754695,
                -104.988116,
                chargers=immutables.Map({mock_l2_charger_id(): 10}),
            ),
        )
        sim = mock_sim(stations=stations, sim_time=36001)
        env = mock_env()
        s1, s2, bs1 = (
            "s1",
            "s2",
            "bs1",
        )  # StationIds in the Denver Downtown scenario
        file = resource_filename(
            "nrel.hive.resources.scenarios.denver_downtown.charging_prices",
            "denver_charging_prices_by_geoid.csv",
        )
        fn = ChargingPriceUpdate.build(file, env.config.input_config.chargers_file)
        result, _ = fn.update(sim, env)
        s1_prices = {c_id: cs.price_per_kwh for c_id, cs in result.stations[s1].state.items()}
        s2_prices = {c_id: cs.price_per_kwh for c_id, cs in result.stations[s2].state.items()}
        bs1_prices = {c_id: cs.price_per_kwh for c_id, cs in result.stations[bs1].state.items()}
        self.assertEqual(
            s1_prices.get(mock_dcfc_charger_id()),
            0.3,
            "station s1 has a DCFC price of 0.3 per kwh",
        )
        self.assertEqual(
            s2_prices.get(mock_dcfc_charger_id()),
            0.3,
            "station s1 has a DCFC price of 0.3 per kwh",
        )
        self.assertEqual(
            bs1_prices.get(mock_l2_charger_id()),
            0.03,
            "station s1 has a LEVEL_2 price of 0.03 per kwh",
        )
        fn.reader.close()

    def test_charge_price_default_price_is_zero(self):
        station = mock_station(
            chargers=immutables.Map(
                {
                    mock_l1_charger_id(): 1,
                    mock_l2_charger_id(): 1,
                    mock_dcfc_charger_id(): 1,
                    # mock_gasoline_pump(): 1
                }
            )
        )
        sim = mock_sim(
            stations=(station,),
            sim_time=1,
            sim_timestep_duration_seconds=1,
        )
        env = mock_env()
        fn = ChargingPriceUpdate.build(None, env.config.input_config.chargers_file)
        result, _ = fn.update(sim, env)
        prices = {c_id: cs.price_per_kwh for c_id, cs in result.stations[station.id].state.items()}
        self.assertEqual(
            prices.get(mock_l1_charger_id()),
            0.0,
            "LEVEL_1 charging should be free by default",
        )
        self.assertEqual(
            prices.get(mock_l2_charger_id()),
            0.0,
            "LEVEL_2 charging should be free by default",
        )
        self.assertEqual(
            prices.get(mock_dcfc_charger_id()),
            0.0,
            "DCFC charging should be free by default",
        )
