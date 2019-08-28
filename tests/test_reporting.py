import os
import shutil
import sys
import unittest
import csv

sys.path.append('../')
from hive import reporting

THIS_DIR = os.path.dirname(os.path.realpath(__file__))
TEST_OUTPUT_DIR = os.path.join(THIS_DIR, '.tmp')

class ReportingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.isdir(TEST_OUTPUT_DIR):
            os.makedirs(TEST_OUTPUT_DIR)

    @classmethod
    def tearDownClass(cls):
        if os.path.isdir(TEST_OUTPUT_DIR):
            shutil.rmtree(TEST_OUTPUT_DIR)

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_generate_logs(self):
        class TestObj:
            def __init__(self, id, data):
                self.ID = id
                self.history = data

        data = [
            {'a': 1, 'b': 'a', 'c': 1.1},
            {'a': 2, 'b': 'b', 'c': 2.2},
            {'a': 3, 'b': 'c', 'c': 3.3},
        ]

        objects = []
        for id in range(10):
            objects.append(TestObj(id, data))

        reporting.generate_logs(objects, TEST_OUTPUT_DIR, context="TEST")

        test_file = os.path.join(TEST_OUTPUT_DIR, 'TEST_1_history.csv')
        with open(test_file, encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                self.assertEqual(dict(row), {k: str(v) for k, v in data[i].items()})


if __name__ == "__main__":
    unittest.main()
