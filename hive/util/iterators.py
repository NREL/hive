from __future__ import annotations

import csv
import logging
from typing import Iterator, Dict, TextIO, Optional, Callable, Tuple, NamedTuple, Iterable, Generator

from itertools import islice, tee
log = logging.getLogger(__name__)


class NamedTupleIterator:
    """
    iterator that deals with a set of named tuples
    """

    def __init__(self, items: Tuple[NamedTuple, ...], step_attr_name: str, stop_condition: Callable):
        self._iterator = iter(items)
        self.step_attr_name = step_attr_name
        self.stop_condition = stop_condition
        self.history = None

    def update_stop_condition(self, stop_condition: Callable):
        self.stop_condition = stop_condition

    def __iter__(self):
        return self

    def __next__(self):
        if self.history:
            # we stored an extra value from last time; return that
            value = getattr(self.history, self.step_attr_name)
            if self.stop_condition(value):
                # stored value is within range
                tmp = self.history
                self.history = None
                return tmp
            else:
                # stored value is not in range
                raise StopIteration
        else:
            item = next(self._iterator)
            value = getattr(item, self.step_attr_name)
            if self.stop_condition(value):
                # value is within range
                return item
            else:
                # set aside row for the future, end iteration
                self.history = item
                raise StopIteration


class DictReaderIterator:
    """
    iterator used internally by DictReaderStepper
    """

    def __init__(self,
                 reader: Iterator[Dict[str, str]],
                 step_column_name: str,
                 stop_condition: Callable,
                 parser: Callable,
                 ):
        self.reader = reader
        self.history = None
        self.step_column_name = step_column_name
        self.stop_condition = stop_condition
        self.parser = parser

    def update_stop_condition(self, stop_condition: Callable):
        self.stop_condition = stop_condition

    def __iter__(self):
        return self

    def __next__(self):

        if self.history:
            # we stored an extra value from last time; return that
            value = self.parser(self.history[self.step_column_name])
            if isinstance(value, Exception):
                raise value

            elif self.stop_condition(value):
                # stored value is within range
                tmp = self.history
                self.history = None
                return tmp
            else:
                # stored value is not in range
                raise StopIteration
        else:
            row = next(self.reader)
            value = self.parser(row[self.step_column_name])
            if isinstance(value, Exception):
                raise value
            elif self.stop_condition(value):
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
                 file_reference: Optional[TextIO],
                 step_column_name: str,
                 initial_stop_condition: Callable = lambda x: x < 0,
                 parser: Callable = lambda x: x,
                 ):
        """
        creates a DictReaderStepper with an internal DictReaderIterator

        :param dict_reader: the dict reader, reading rows from a csv file
        :param step_column_name: the column we are comparing new bounds against
        :param initial_stop_condition: the initial bounds - set low (zero) for ascending, high (inf) for descending
        :param parser: an optional parameter for parsing the input_config value
        """
        self._iterator = DictReaderIterator(dict_reader, step_column_name, initial_stop_condition, parser)
        self._file = file_reference

    @classmethod
    def build(cls,
              file: str,
              step_column_name: str,
              initial_stop_condition: Callable = lambda x: x < 0,
              parser: Callable = lambda x: x,
              ) -> Tuple[Optional[Exception], Optional[DictReaderStepper]]:
        """
        alternative constructor that takes a file path and returns a DictReaderStepper, or, a failure

        :param file: the file path
        :param step_column_name: the column we are comparing new bounds against
        :param initial_stop_condition: the initial bounds - set low (zero) for ascending, high (inf) for descending
               note: descending not yet implemented
        :param parser: an optional parameter for parsing the input_config value
        :return: a new reader or an exception
        """
        try:
            f = open(file, 'r')
            return None, cls(csv.DictReader(f), f, step_column_name, initial_stop_condition, parser)
        except Exception as e:
            return e, None

    @classmethod
    def from_iterator(cls,
                      data: Iterator[Dict[str, str]],
                      step_column_name: str,
                      initial_stop_condition: Callable = lambda x: x < 0,
                      parser: Callable = lambda x: x,
                      ) -> DictReaderStepper:
        """
        allows for substituting a simple Dict Iterator in place of loading from
        a file, allowing for programmatic data loading (for debugging, or, for
        dealing with default file contents)

        :param data: a provider of row-wise data similar to a CSV
        :param step_column_name: the key we are expecting in each Dict that we are comparing new bounds against
        :param initial_stop_condition: the initial bounds - set low (zero) for ascending, high (inf) for descending
               note: descending not yet implemented

        :param parser: an optional parameter for parsing the input_config value
        :return: a new reader or an exception
        """
        return cls(data, None, step_column_name, initial_stop_condition, parser)

    def read_until_stop_condition(self, stop_condition: Callable) -> Iterator[Dict[str, str]]:
        """
        reads rows from the DictReader as long as step_column_name is less than or equal to "value"

        :param stop_condition: the condition to validate. we will read all new
                      rows as long as each row's value evaluates to True
        :return: the updated DictReaderStepper and a tuple of rows, which may be empty if no new rows are consumable.
        """
        self._iterator.update_stop_condition(stop_condition)
        return self._iterator

    def close(self):
        if self._file:
            self._file.close()


def sliding(iterable: Iterable, size: int) -> Generator:
    """
    iterate a sliding window over some iterable with a fixed window size
    taken from [[https://codereview.stackexchange.com/a/239386]]
    :param iterable: the iterable to traverse
    :param size: the window size for sliding
    :return: an iterable of sliding windows over the original iterator
    """
    iterables = tee(iter(iterable), size)
    window = zip(*(islice(t, n, None) for n, t in enumerate(iterables)))
    yield from window
