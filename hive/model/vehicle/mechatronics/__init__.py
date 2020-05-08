from __future__ import annotations

from csv import DictReader
from typing import Dict

from hive.model.vehicle.mechatronics.bev import BEV
from hive.model.vehicle.mechatronics.interface import MechatronicsInterface
from hive.util.typealiases import MechatronicsId

mechatronic_models = {
    'bev': BEV,
}


def build_mechatronics_table(file: str) -> Dict[MechatronicsId, MechatronicsInterface]:
    mechatronics = {}
    with open(file) as f:
        reader = DictReader(f)
        for row in reader:
            try:
                mechatronics_id = row['mechatronics_id']
                mechatronics_type = row['mechatronics_type']
            except KeyError:
                raise IOError(f'could not find mechatronics_id and mechatronics_type in {file}')
            try:
                model = mechatronic_models[mechatronics_type]
            except KeyError:
                raise IOError(f'{mechatronics_type} not registered with hive')
            mechatronics[mechatronics_id] = model.from_dict(row)

    return mechatronics
