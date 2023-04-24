# from nrel.hive.model.sim_time import SimTime
#
# from nrel.hive import HiveConfig
from nrel.hive.reporting.handler.time_step_stats_handler import TimeStepStatsHandler


# class MockSim:
#     def start_time(self):
#         return SimTime.build(180)
# class MockConfig:
#     def sim(self):
#         return MockSim()

def test_close():
    handler = TimeStepStatsHandler(None, None, None)