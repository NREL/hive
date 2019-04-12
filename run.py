"""
Run hive w/ inputs defined in config.py
"""
import sys
import random
import config as cfg
from datetime import datetime
import hive.preprocess as pp

if __name__ == "__main__":
    random.seed(22)
    today = datetime.now()
    date = "{0}-{1}-{2}".format(today.month, today.day, today.year)

    #Combine requests files, add pax count if not exists
    reqs_df = pp.load_requests(cfg.REQUEST_PATH)
    print(reqs_df.head())

    #Pool requests - from hive.pool, module for various pooling types - o/d, dynamic, n/a
    #pooled_reqs_df.to_csv(cfg.OUT_PATH, index=False)





    
