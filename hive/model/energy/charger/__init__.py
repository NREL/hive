from csv import DictReader
from pathlib import Path
from typing import Dict

from hive.model.energy.charger.charger import Charger
from hive.util.typealiases import ChargerId


def build_chargers_table(chargers_file: str) -> Dict[ChargerId, Charger]:
    """
    constructs a table of the chargers available in this simulation
    :param chargers_file: the source chargers file
    :return: the chargers table for this Environment
    :raises: IOError
    """

    chargers_file_path = Path(chargers_file)
    if not chargers_file_path.is_file():
        raise IOError(f"attempting to load chargers file {chargers_file} which does not exist")
    else:
        chargers_table = {}
        with chargers_file_path.open() as f:
            reader = DictReader(f)
            for row in reader:
                charger_id = row.get('charger_id')
                power_kw = row.get('power_kw')
                if not charger_id:
                    raise IOError(f"charger row missing charger_id field: {row}")
                elif not power_kw:
                    raise IOError(f"charger row missing power_kw field: {row}")
                else:
                    new_charger = Charger(id=charger_id, power_kw=power_kw)
                    chargers_table.update({charger_id: new_charger})
        return chargers_table
