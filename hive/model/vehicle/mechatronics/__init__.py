from __future__ import annotations

from typing import Dict
from pathlib import Path

import yaml

from hive.model.vehicle.mechatronics.bev import BEV
from hive.model.vehicle.mechatronics.ice import ICE
from hive.model.vehicle.mechatronics.mechatronics_interface import MechatronicsInterface
from hive.util import fs
from hive.util.typealiases import MechatronicsId

mechatronic_models = {
    'bev': BEV,
    'ice': ICE,
}


def build_mechatronics_table(mechatronics_file: str, scenario_directory: str) -> Dict[
    MechatronicsId, MechatronicsInterface]:
    """
    constructs a dictionary containing all of the provided vehicle configurations where the key is the mechatronics ID
    and the contents are the appropriate mechatronics models with the desired attributes


    :param mechatronics_file: the mechatronics configuration yaml file

    :param scenario_directory: the directory with the required scenario files
    :return: a dictionary of the different vehicle configurations where the keys are the mechatronics IDs
    :raises Exception due to IOErrors, missing required parameters in the mechatronics yaml
    :raises Exception due to FileNotFoundErrors, missing the mechatronics, powertrain, or powercurve file(s)
    """
    mechatronics = {}
    with open(mechatronics_file) as f:
        config_dict = yaml.safe_load(f)
        for mechatronics_id in config_dict:
            # add the mechatronics id to the nested dictionary
            config_dict[mechatronics_id]['mechatronics_id'] = mechatronics_id
            try:
                mechatronics_type = config_dict[mechatronics_id]['mechatronics_type']
            except KeyError:
                raise IOError(f'could not find mechatronics_type in {mechatronics_id}')
            try:
                model = mechatronic_models[mechatronics_type]
            except KeyError:
                raise IOError(f'{mechatronics_type} not registered with hive')

            if "powertrain_file" in config_dict[mechatronics_id]:
                powertrain_file = fs.construct_asset_path(
                    config_dict[mechatronics_id]['powertrain_file'],
                    scenario_directory,
                    "powertrain",
                    "powertrain"  # resources.powertrain
                )
                config_dict[mechatronics_id]['powertrain_file'] = powertrain_file

            if "powercurve_file" in config_dict[mechatronics_id]:
                powercurve_file = fs.construct_asset_path(
                    config_dict[mechatronics_id]['powercurve_file'],
                    scenario_directory,
                    "powercurve",
                    "powercurve"  # resources.powercurve
                )
                config_dict[mechatronics_id]['powercurve_file'] = powercurve_file

            mechatronics[mechatronics_id] = model.from_dict(config_dict[mechatronics_id])

    return mechatronics
