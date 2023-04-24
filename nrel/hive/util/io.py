import csv
import pathlib
from collections.abc import Iterable

def to_csv(data: Iterable, path: pathlib.Path):
    with open(path, 'w') as f:
        writer = csv.writer(f)
        writer.writerows(data)
