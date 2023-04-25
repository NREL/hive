import csv
import pathlib
from collections.abc import Sequence
from typing import Union


def to_csv(data: Sequence[Union[dict, list]], path: pathlib.Path):
    with open(path, 'w') as f:
        if all(isinstance(row, dict) for row in data):
            writer = csv.DictWriter(f, fieldnames=[header for header in data[0].keys()])
            writer.writeheader()
        else:
            writer = csv.writer(f)
        writer.writerows(data)

