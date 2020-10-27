from csv import DictReader
from pathlib import Path
from typing import Dict

from hive.model.energy.charger.charger import Charger
from hive.model.energy.energytype import EnergyType
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
                energy_type_srt = row.get('energy_type')
                rate_str = row.get('rate')
                units = row.get('units')
                if not charger_id:
                    raise IOError(f"charger row missing charger_id field: {row}")
                elif not rate_str:
                    raise IOError(f"charger row missing rate field: {row}")
                elif not energy_type_srt:
                    raise IOError(f"charger row missing energy_type field: {row}")
                elif not units:
                    raise IOError(f"charger row missing units field: {row}")
                else:
                    try:
                        rate = float(rate_str)
                    except TypeError as e:
                        raise TypeError(f"unable to parse charger rate as number for row {row}") from e
                    energy_type = EnergyType.from_string(energy_type_srt)
                    if not energy_type:
                        raise TypeError(f"unable to parse energy type for row {row}")
                    new_charger = Charger(id=charger_id, energy_type=energy_type, rate=rate, units=units)
                    chargers_table.update({charger_id: new_charger})
        return chargers_table
