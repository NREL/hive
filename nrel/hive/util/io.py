import csv
import pathlib

from nrel.hive.util.type_hints import HiveTabularData, HiveTabularDataDicts


def to_csv(data: HiveTabularData, path: pathlib.Path):
    with open(path, 'w') as f:
        writer = csv.writer(f)
        writer.writerows(data)

def to_csv_dicts(data: HiveTabularDataDicts, path: pathlib.Path):
    with open(path, 'w') as f:
        writer = csv.DictWriter(f, fieldnames=[header for header in data[0].keys()])
        writer.writeheader()
        writer.writerows(data)