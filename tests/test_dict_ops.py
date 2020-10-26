from unittest import TestCase

import immutables
from typing import FrozenSet

from hive.util import DictOps


class TestDictOps(TestCase):
    def test_add_to_dict(self):
        m = immutables.Map()
        result = DictOps.add_to_dict(m, "a", 500)
        self.assertEqual(result["a"], 500, "should have stored the value 500 at key 'a'")

    def test_remove_from_dict(self):
        m = immutables.Map({'a': 500})
        result = DictOps.remove_from_dict(m, 'a')
        self.assertNotIn('a', result, "should have removed key 'a'")

    def test_merge_dicts(self):
        lhs = immutables.Map({'a': 1, 'b': 9})
        rhs = immutables.Map({'b': 2, 'c': 3})
        result = DictOps.merge_dicts(lhs, rhs)
        self.assertEqual(result['a'], 1, "should have 'a' from lhs")
        self.assertEqual(result['b'], 2, "should have 'b' from rhs")
        self.assertEqual(result['c'], 3, "should have 'c' from rhs")

    def test_add_to_collection_dict(self):
        some_locs = immutables.Map({'1234': frozenset(['v1', 'v2'])})
        update_at_loc = DictOps.add_to_collection_dict(some_locs, '1234', 'v3')
        update_empty_loc = DictOps.add_to_collection_dict(some_locs, '5678', 'v4')
        self.assertIn('v3', update_at_loc.get('1234'), "v3 should be added at location 1234")
        self.assertIn('v1', update_at_loc.get('1234'), "v1 should not have been removed at location 1234")
        self.assertIn('v2', update_at_loc.get('1234'), "v2 should not have been removed at location 1234")
        self.assertIn('5678', update_empty_loc.keys(), "location 1234 should be added")
        self.assertIn('v4', update_empty_loc.get('5678'), "v4 should be added to new location 5678")

    def test_remove_from_collection_dict(self):
        some_locs = immutables.Map({'1234': frozenset(['v1', 'v2']), '5678': frozenset(['v3',])})
        update_at_loc = DictOps.remove_from_collection_dict(some_locs, '1234', 'v1')
        update_empties_loc = DictOps.remove_from_collection_dict(some_locs, '5678', 'v3')
        self.assertNotIn('v1', update_at_loc.get('1234'), "v1 should have been removed at location 1234")
        self.assertIn('v2', update_at_loc.get('1234'), "v2 should not have been removed at location 1234")
        self.assertNotIn('5678', update_empties_loc.keys(), "location 5678 should have been emptied")

        with self.assertRaises(KeyError) as raised:
            DictOps.remove_from_collection_dict(some_locs, '910_', 'v4')

        self.assertIsInstance(raised.exception, KeyError, "should have raised a KeyError")
