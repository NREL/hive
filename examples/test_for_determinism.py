from pathlib import Path
from typing import Dict, List
from pkg_resources import resource_filename
from nrel.hive.initialization.load import load_config, load_simulation
import random
import numpy
import pandas
import argparse
import sys

from nrel.hive.runner.local_simulation_runner import LocalSimulationRunner

# this utility demonstrates a set of runs have the same high-level results
if __name__ == "__main__":
    denver = Path(resource_filename(
            "nrel.hive.resources.scenarios.denver_downtown", 
            "denver_demo.yaml"))
    parser = argparse.ArgumentParser()
    parser.add_argument('--scenario', type=Path, default=denver)
    parser.add_argument('--iterations', type=int, default=5)
    parser.add_argument('--outfile', type=Path, required=False)
    args = parser.parse_args()
    
    iterations = args.iterations
    data: List[Dict] = []
    for i in range(iterations):
        # set up config with scenario + limited (stats only) logging
        config_no_log = load_config(args.scenario).suppress_logging()
        config = config_no_log._replace(
            global_config=config_no_log.global_config._replace(
                log_stats=True
            )
        )
        # set random seed from Sim config
        if config.sim.seed is not None:
            random.seed(config.sim.seed)
            numpy.random.seed(config.sim.seed)

        rp0 = load_simulation(config)
        rp1 = LocalSimulationRunner.run(rp0)
        stats = rp1.e.reporter.get_summary_stats(rp1)
        if stats is None:
            raise Exception("hive result missing stats object")
        stats['iteration'] = i
        # flatten vehicle states
        vs = stats['vehicle_state'].copy()
        del stats['vehicle_state']
        for k, v in vs.items():
            stats[f'{k}StatePct'] = v['observed_percent']
            stats[f'{k}StateVkt'] = v['vkt']

        data.append(stats)
        print(f"finished iteration {i}")


    df = pandas.DataFrame(data)
    
    test_cols = [
        'mean_final_soc',
        'requests_served_percent',
        'total_vkt',
        'total_kwh_expended',
        'total_gge_expended',
        'total_kwh_dispensed',
        'total_gge_dispensed'
    ]
    
    print(f'testing for determinism between {args.iterations} runs')
    exit_code = 0
    for col in test_cols:
        n = df[col].nunique()
        if n == 1:
            print(f'{col} is good, all values match')
        else:
            exit_code = 1
            entries = '[' + ', '.join(df[col].unique()) + ']'
            print(f'{col} no good, has {n} unique entries (should be one): {entries}')
    
    if args.outfile:
        df.to_csv(args.outfile)

    sys.exit(exit_code)