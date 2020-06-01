from pathlib import Path

import yaml

from hive.model.vehicle.mechatronics.powertrain.powertrain import Powertrain
from hive.model.vehicle.mechatronics.powertrain.tabular_powertrain import TabularPowertrain

powertrain_models = {
    'tabular': TabularPowertrain
}


def build_powertrain(config: dict) -> Powertrain:
    try:
        file = config['powertrain_file']
    except KeyError:
        raise AttributeError("Can't build powertrain without powertrain file")

    with Path(config['powertrain_file']).open() as f:
        powertrain_file_contents = yaml.safe_load(f)
        powertrain_type = powertrain_file_contents.get('type')

        # pass config from caller merged with the file contents
        config.update(powertrain_file_contents)

        if not powertrain_type:
            raise KeyError(f"powertrain file {file} missing required 'type' field")
        elif powertrain_type not in powertrain_models:
            raise IOError(f"PowerCurve with type {powertrain_type} is not recognized, must be one of {powertrain_models.keys()}")
        else:
            return powertrain_models[powertrain_type](data=config)
