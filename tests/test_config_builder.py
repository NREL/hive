from typing import NamedTuple, Dict
from unittest import TestCase

from hive.config import ConfigBuilder
from hive.model.roadnetwork.link import Link


class TestConfigBuilder(TestCase):
    def test_build_using_defaults(self):

        defaults = {
            'a': 1,
            'b': "string",
            'c': Link("test", "o", "d")
        }

        test_class = ConfigBuilder.build(
            default_config=defaults,
            required_config={},
            config_constructor=TestConfigBuilderAssets.constructor,
            config=None
        )

        self.assertIsInstance(test_class, TestConfigBuilderAssets.TestClass)
        self.assertEqual(test_class.a, defaults['a'])
        self.assertEqual(test_class.b, defaults['b'])
        self.assertEqual(test_class.c, defaults['c'])

    def test_build_has_required_fields(self):
        required = {
            'a': int,
            'b': str,
            'c': Link
        }

        config = {
            'a': 6,
            'b': 'foo',
            'c': Link("ya", "asdf", "jkl;")
        }

        test_class = ConfigBuilder.build(
            default_config={},
            required_config=required,
            config_constructor=TestConfigBuilderAssets.constructor,
            config=config
        )

        self.assertIsInstance(test_class, TestConfigBuilderAssets.TestClass)
        self.assertEqual(test_class.a, config['a'])
        self.assertEqual(test_class.b, config['b'])
        self.assertEqual(test_class.c, config['c'])

    def test_build_missing_required_field(self):
        required = {
            'a': int,
            'b': str,
            'c': Link
        }

        config = {
            'a': 6,
            'c': Link("ya", "asdf", "jkl;")
        }

        with self.assertRaises(AttributeError):
            test_class = ConfigBuilder.build(
                default_config={},
                required_config=required,
                config_constructor=TestConfigBuilderAssets.constructor,
                config=config
            )


    def test_build_ignores_extra_fields(self):
        config = {
            'a': 6,
            'b': 'foo',
            'c': Link("ya", "asdf", "jkl;"),
            'extra': "will be ignored",
            'd': {
                'e': Link("1", "2", "3")
            }
        }

        test_class = ConfigBuilder.build(
            default_config={},
            required_config={},
            config_constructor=TestConfigBuilderAssets.constructor,
            config=config
        )

        self.assertIsInstance(test_class, TestConfigBuilderAssets.TestClass)
        self.assertEqual(test_class.a, config['a'])
        self.assertEqual(test_class.b, config['b'])
        self.assertEqual(test_class.c, config['c'])


class TestConfigBuilderAssets:
    class TestClass(NamedTuple):
        a: int
        b: str
        c: Link

    @classmethod
    def constructor(cls, d: Dict):
        return TestConfigBuilderAssets.TestClass(d['a'], d['b'], d['c'])