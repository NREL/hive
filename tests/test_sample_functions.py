from unittest import TestCase

from returns.primitives.exceptions import UnwrapFailedError
from returns.result import Result

from hive.initialization.sample_requests import default_request_sampler
from hive.initialization.sample_vehicles import sample_vehicles, build_default_location_sampling_fn, \
    build_default_soc_sampling_fn
from hive.resources.mock_lobster import *


class TestSampleVehicles(TestCase):

    def test_sample_n_requests_default(self):
        n = 100
        sim = mock_sim(road_network=mock_osm_network())
        env = mock_env()

        sample_requests = default_request_sampler(n, sim, env)

        self.assertEquals(len(sample_requests), n, f"should have sampled {n} requests")

        for r in sample_requests:
            self.assertNotEqual(r.origin, r.destination, f"request should not have equal origin and destination")

    def test_sample_n_vehicles_default(self):
        """
        samples 10 vehicles and expects them to be instantiated with full charge at the same base location
        """
        n = 10
        base = mock_base()
        bases = (base,)
        sim = mock_sim(bases=bases, road_network=mock_osm_network())
        env = mock_env()
        mechatronics_id = DefaultIds.mock_mechatronics_bev_id()
        loc_fn = build_default_location_sampling_fn()
        soc_fn = build_default_soc_sampling_fn()

        result: Result = sample_vehicles(
            count=n,
            sim=sim,
            env=env,
            location_sampling_function=loc_fn,
            soc_sampling_function=soc_fn
        )

        def check_vehicle(v: Vehicle):
            self.assertEquals(v.mechatronics_id, DefaultIds.mock_mechatronics_bev_id())
            self.assertEquals(v.energy.get(EnergyType.ELECTRIC),
                              env.mechatronics.get(mechatronics_id).battery_capacity_kwh)
            self.assertEquals(v.position, base.position)

        self.assertEqual(len(result.unwrap().vehicles), n, f"should have {n} vehicles")
        map(check_vehicle, result.unwrap().vehicles.values())

    def test_sample_n_with_failure(self):
        """
        this test is really just here to help demonstrate the Returns library.
        instead of blowing up in the sample_vehicles reduce loop, we get the first
        error result after 4 items succeed. this is because of the "railway" programming
        aka fail-fast feature of Monads, where we only call "bind" when in the Success path.
        """
        n = 10
        fail_at_vehicle_n = 4
        failure_msg = f"fails after {fail_at_vehicle_n} attempts"
        base = mock_base()
        bases = (base,)
        sim = mock_sim(bases=bases, road_network=mock_osm_network())
        env = mock_env()

        self.wonky_fn_calls = 0

        def wonky_loc_fn(s) -> Link:
            self.wonky_fn_calls += 1
            if self.wonky_fn_calls == fail_at_vehicle_n:
                raise AttributeError(failure_msg)
            fn = build_default_location_sampling_fn()
            return fn(s)

        soc_fn = build_default_soc_sampling_fn()

        result: Result = sample_vehicles(
            count=n,
            sim=sim,
            env=env,
            location_sampling_function=wonky_loc_fn,
            soc_sampling_function=soc_fn
        )

        with self.assertRaises(UnwrapFailedError):
            result.unwrap()
        self.assertEquals(result._inner_value.args[0], failure_msg)
