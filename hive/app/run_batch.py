from __future__ import annotations

import argparse
import logging
import os
import traceback
from multiprocessing import Pool
from pathlib import Path
from typing import TYPE_CHECKING, NamedTuple, List

import yaml

from hive.app.run import run_sim
from hive.util import fs

if TYPE_CHECKING:
    pass

parser = argparse.ArgumentParser(description="run hive")
parser.add_argument(
    'batch_config',
    help='which batch config file to use?'
)

log = logging.getLogger("hive")


class BatchConfig(NamedTuple):
    scenario_files: List[Path]

    @classmethod
    def from_dict(cls, d: dict) -> BatchConfig:
        if 'scenario_files' not in d:
            raise KeyError("must specify scenario_files in the batch config")

        scenario_files = [fs.find_scenario(f) for f in d['scenario_files']]

        return BatchConfig(scenario_files)


class SimArgs(NamedTuple):
    scenario_file: Path
    position: int


def safe_sim(sim_args: SimArgs) -> int:
    try:
        return run_sim(sim_args.scenario_file, sim_args.position)
    except Exception:
        log.error(f"{sim_args.scenario_file} failed, see traceback:")
        log.error(traceback.format_exc())
        return -1


def run() -> int:
    """
    entry point for a hive application run
    :return: 0 if success, 1 if error
    """

    _welcome_to_hive()

    # parse arguments
    args = parser.parse_args()

    # main application
    config_file = Path(args.batch_config)
    if not config_file.is_file():
        raise FileNotFoundError(f"couldn't find config file: {config_file}")

    with config_file.open('r') as stream:
        d = yaml.safe_load(stream)
        config = BatchConfig.from_dict(d)

    sim_args = [SimArgs(f, i) for i, f in enumerate(config.scenario_files)]

    # check to make sure we don't exceed system CPU
    max_cpu = os.cpu_count()

    if len(config.scenario_files) > max_cpu:
        cpu = max_cpu
    else:
        cpu = len(config.scenario_files)

    with Pool(cpu) as p:
        results = p.map(safe_sim, sim_args)

    return 0


def _welcome_to_hive():
    welcome = """
##     ##  ####  ##     ##  #######
##     ##   ##   ##     ##  ##
#########   ##   ##     ##  ######
##     ##   ##    ##   ##   ##
##     ##  ####     ###     #######

                .' '.            __
       .        .   .           (__\_
        .         .         . -{{_(|8)
          ' .  . ' ' .  . '     (__/
    """

    log.info(welcome)


if __name__ == "__main__":
    run()
