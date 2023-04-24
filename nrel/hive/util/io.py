import csv
import pathlib
from typing import Union


def to_csv(data: list[Union[dict, list]], path: pathlib.Path):
    with open(path, 'w') as f:
        if all(isinstance(row, dict) for row in data):
            writer = csv.DictWriter(f, fieldnames=[header for header in data[0].keys()])
            writer.writeheader()
        else:
            writer = csv.writer(f)
        writer.writerows(data)

