from pathlib import Path
from typing import Any, Dict, Type

import yaml

from nrel.hive.model.vehicle.mechatronics.powertrain.powertrain import Powertrain
from nrel.hive.model.vehicle.mechatronics.powertrain.tabular_powertrain import TabularPowertrain

DEFAULT_MODELS: Dict[str, Type[Powertrain]] = {"tabular": TabularPowertrain}


def build_powertrain(config: Dict[str, Any]) -> Powertrain:
    try:
        file = config["powertrain_file"]
    except KeyError:
        raise AttributeError("Can't build powertrain without powertrain file")

    with Path(config["powertrain_file"]).open() as f:
        powertrain_file_contents = yaml.safe_load(f)
        powertrain_type = powertrain_file_contents.get("type")

        # pass config from caller merged with the file contents
        config.update(powertrain_file_contents)

        if not powertrain_type:
            raise KeyError(f"powertrain file {file} missing required 'type' field")
        elif powertrain_type not in DEFAULT_MODELS:
            raise IOError(
                f"PowerCurve with type {powertrain_type} is not recognized, must be one of {DEFAULT_MODELS.keys()}"
            )
        else:
            return DEFAULT_MODELS[powertrain_type].from_data(data=config)
