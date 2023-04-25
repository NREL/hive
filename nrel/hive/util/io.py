import csv
import pathlib
from typing import Sequence


def to_csv(data: Sequence[Sequence[str]], path: pathlib.Path):
    with open(path, "w") as f:
        writer = csv.writer(f)
        writer.writerows(data)


def to_csv_dicts(data: Sequence[dict], path: pathlib.Path):
    with open(path, "w") as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
