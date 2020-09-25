from __future__ import annotations

import yaml
from typing import Dict

from hive.config.input import Input
from hive.model.vehicle.mechatronics.bev import BEV
from hive.model.vehicle.mechatronics.ice import ICE
from hive.model.vehicle.mechatronics.mechatronics_interface import MechatronicsInterface
from hive.util import fs
from hive.util.typealiases import MechatronicsId

mechatronic_models = {
    'bev': BEV,
    'ice': ICE,
}


def build_mechatronics_table(input: Input) -> Dict[MechatronicsId, MechatronicsInterface]:
    mechatronics = {}
    with open(input.mechatronics_file) as f:
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
            if mechatronics_type == 'bev':
                try:
                    powertrain_file = config_dict[mechatronics_id]['powertrain_file']
                    powercurve_file = config_dict[mechatronics_id]['powercurve_file']
                except KeyError as err:
                    raise FileNotFoundError() from err
                try:
                    # find the appropriate powertrain and powercurve resource
                    powertrain_file = fs.construct_asset_path(
                        powertrain_file,
                        input.scenario_directory,
                        "powertrain",
                        "powertrain"  # resources.powertrain
                    )
                    powercurve_file = fs.construct_asset_path(
                        powercurve_file,
                        input.scenario_directory,
                        "powercurve",
                        "powercurve"  # resources.powercurve
                    )
                    config_dict[mechatronics_id]['powertrain_file'] = powertrain_file
                    config_dict[mechatronics_id]['powercurve_file'] = powercurve_file

                except FileNotFoundError as e:
                    raise e

            mechatronics[mechatronics_id] = model.from_dict(config_dict[mechatronics_id])

    return mechatronics
