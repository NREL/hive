from typing import List, Mapping, TypeVar

T = TypeVar("T")


def validate_fields(row: Mapping[str, T], expected: List[str]):
    """
    checks whether all expected fields/columns exist on some mapping

    :param row: based off of row representations in DictReader, this is a
                mapping from column name to colunm value for a row
    :param expected: the expected column names for this row
    :raises ValueError: for all column names missing
    """
    missing = [field for field in expected if field not in row]
    if len(missing) == 0:
        return
    else:
        plural = "fields" if len(missing) > 0 else "field"
        fields = ", ".join(missing)
        msg = f"station from row failed, missing {plural} [{fields}]"
        raise ValueError(msg)
