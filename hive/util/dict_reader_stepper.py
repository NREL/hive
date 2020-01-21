from __future__ import annotations

import csv
from typing import Iterator, Dict, Union, TextIO


class DictReaderIterator:
    """
    iterator used internally by DictReaderStepper
    """

    def __init__(self,
                 reader: Iterator[Dict[str, str]],
                 step_column_name: str,
                 stop_value: float):
        self.reader = reader
        self.history = None
        self.step_column_name = step_column_name
        self.stop_value = stop_value

    def update_stop_value(self, new_value: float):
        self.stop_value = new_value

    def __iter__(self):
        return self

    def __next__(self):

        if self.history:
            # we stored an extra value from last time; return that
            if float(self.history[self.step_column_name]) < self.stop_value:
                # stored value is within range
                tmp = self.history
                self.history = None
                return tmp
            else:
                # stored value is not in range
                raise StopIteration
        else:
            row = next(self.reader)
            if float(row[self.step_column_name]) < self.stop_value:
                # value is within range
                return row
            else:
                # set aside row for the future, end iteration
                self.history = row
                raise StopIteration


class DictReaderStepper:
    """
    takes a DictReader and steps through it, using one specific column's values as a way to split
    iteration over windows (of time, or other).

    read_until_value consumes the next set of rows that fall within the next upper-value for the next window.

    destruction: should be explicitly closed via DictReaderStepper.close()
    """

    def __init__(self,
                 dict_reader: Iterator[Dict[str, str]],
                 file_reference: TextIO,
                 step_column_name: str,
                 initial_stop_value: float = 0
                 ):
        """
        creates a DictReaderStepper with an internal DictReaderIterator
        :param dict_reader: the dict reader, reading rows from a csv file
        :param step_column_name: the column we are comparing new bounds against
        :param initial_stop_value: the initial bounds - set low (zero) for ascending, high (inf) for descending
        """
        self._iterator = DictReaderIterator(dict_reader, step_column_name, initial_stop_value)
        self._file = file_reference

    @classmethod
    def from_file(cls,
                  file: str,
                  step_column_name: str,
                  initial_stop_value: float = 0) -> Union[Exception, DictReaderStepper]:
        """
        alternative constructor that takes a file path and returns a DictReaderStepper, or, a failure
        :param file: the file path
        :param step_column_name: the column we are comparing new bounds against
        :param initial_stop_value: the initial bounds - set low (zero) for ascending, high (inf) for descending
        :return:
        """
        try:
            f = open(file, 'r')
            return cls(csv.DictReader(f), f, step_column_name, initial_stop_value)
        except Exception as e:
            return e

    def read_until_value(self, bounds: float) -> Iterator[Dict[str, str]]:
        """
        reads rows from the DictReader as long as step_column_name is less than or equal to "value"
        :param bounds: the value, such as a second_of_day to compare against. we will read all new
                      rows as long as each row's value is less than or equal to this
        :return: the updated DictReaderStepper and a tuple of rows, which may be empty if no new rows are consumable.
        """
        self._iterator.update_stop_value(bounds)
        return self._iterator

    def close(self):
        self._file.close()
