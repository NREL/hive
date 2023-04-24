import csv
from collections.abc import Iterable

def to_csv(data: Iterable, path: str):
    with open(path, 'w') as f:
        writer = csv.writer(f)
        writer.writerows(data)
