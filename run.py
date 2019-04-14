"""
Run hive w/ inputs defined in config.py
"""
import sys
import random
import config as cfg
from datetime import datetime
import hive.preprocess as pp

if __name__ == "__main__":
    random.seed(22) #seed for pax distr sampling
    today = datetime.now()
    date = "{0}-{1}-{2}".format(today.month, today.day, today.year)

    print("#"*30)
    print("Starting Simulation")
    print("#"*30)
    print()

    print("Processing requests")
    #Combine requests files, add pax count if not exists
    reqs_df = pp.load_requests(cfg.REQUEST_PATH)
    print("loaded {} requests".format(len(reqs_df)))
    
    #Filter requests where distance < 0.05 miles
    reqs_df = pp.filter_short_trips(reqs_df, min_miles=0.05)
    print("filtered requests violating min distance req, {} remain".format(len(reqs_df)))

    #Filter requests where pickup/dropoff location outside operating area
    reqs_df = pp.filter_requests_outside_oper_area(reqs_df, cfg.OPERATING_AREA_PATH)
    print("filtered requests outside of operating area, {} remain".format(len(reqs_df)))

    #Pool requests - from hive.pool, module for various pooling types - o/d, dynamic, n/a

    #reqs_df.to_csv(cfg.OUT_PATH + sim_name + 'requests/' + requests_filename, index=False)

    #Create output paths - 







    
