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

from nrel.hive.app import run
from nrel.hive.config import HiveConfig
from nrel.hive.dispatcher import *
from nrel.hive.state.simulation_state.update.step_simulation import StepSimulation
from nrel.hive.state.simulation_state.update.update import Update


def package_root() -> Path:
    return Path(__file__).parent


from rich.logging import RichHandler


FORMAT = "%(message)s"
rich_handler = RichHandler(markup=True, rich_tracebacks=True, show_time=False, show_path=False)
logging.basicConfig(
    level=logging.INFO,
    format=FORMAT,
    handlers=[rich_handler],
)
