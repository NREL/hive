__doc__ = r"""

##     ##  ####  ##     ##  #######
##     ##   ##   ##     ##  ##
#########   ##   ##     ##  ######
##     ##   ##    ##   ##   ##
##     ##  ####     ###     #######

                .' '.            __
       .        .   .           (__\_
        .         .         . -{{_(|8)
          ' .  . ' ' .  . '     (__/


**HIVE** is a Python application for simulating the effects of hypothetical 
mobility as a service (MaaS) applications on 
infrastructure, levels of service, and additional energy outcomes. Developed in
2019 at the National Renewable Energy Laboratory (NREL), HIVE is an
agent-based model that simulates MaaS operations over real world trip data.
"""

import logging

from pathlib import Path

from tqdm import tqdm

from nrel.hive.app import run
from nrel.hive.config import HiveConfig
from nrel.hive.dispatcher import *
from nrel.hive.state.simulation_state.update.update import Update
from nrel.hive.state.simulation_state.update.step_simulation import (
    StepSimulation,
)


def package_root() -> Path:
    return Path(__file__).parent


class TqdmHandler(logging.StreamHandler):
    def emit(self, record):
        msg = self.format(record)
        tqdm.write(msg)


# dictConfig(LOGGING_CONFIG)
log = logging.getLogger()
log.setLevel(logging.INFO)

formatter = logging.Formatter("[%(levelname)s] - %(name)s - %(message)s")

sh = TqdmHandler()
sh.setLevel(logging.INFO)
sh.setFormatter(formatter)

log.addHandler(sh)
