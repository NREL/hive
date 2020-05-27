from __future__ import annotations

from csv import DictReader
from typing import Dict

from hive.config.input import Input
from hive.model.vehicle.mechatronics.bev import BEV
from hive.model.vehicle.mechatronics.mechatronics_interface import MechatronicsInterface
from hive.util import fs
from hive.util.typealiases import MechatronicsId

mechatronic_models = {
    'bev': BEV,
}


def build_mechatronics_table(input: Input) -> Dict[MechatronicsId, MechatronicsInterface]:
    mechatronics = {}
    with open(input.mechatronics_file) as f:
        reader = DictReader(f)
        for row in reader:
            try:
                mechatronics_id = row['mechatronics_id']
                mechatronics_type = row['mechatronics_type']
            except KeyError:
                raise IOError(f'could not find mechatronics_id and mechatronics_type in {input.mechatronics_file}')
            try:
                model = mechatronic_models[mechatronics_type]
            except KeyError:
                raise IOError(f'{mechatronics_type} not registered with hive')
            try:
                powertrain_file = row['powertrain_file']
                powercurve_file = row['powercurve_file']
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
                row['powertrain_file'] = powertrain_file
                row['powercurve_file'] = powercurve_file

            except FileNotFoundError as e:
                raise e

            mechatronics[mechatronics_id] = model.from_dict(row)

    return mechatronics
