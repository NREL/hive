from typing import NamedTuple, Dict
from unittest import TestCase

from hive.config.config_builder import ConfigBuilder


class TestConfigBuilder(TestCase):
    def test_build_using_defaults(self):
        defaults = {
            'a': 1,
            'b': "string",
        }

        test_class = ConfigBuilder.build(
            default_config=defaults,
            required_config=(),
            config_constructor=TestConfigBuilderAssets.constructor,
            config=None
        )

        self.assertIsInstance(test_class, TestConfigBuilderAssets.TestClass)
        self.assertEqual(test_class.a, defaults['a'])
        self.assertEqual(test_class.b, defaults['b'])

    def test_build_has_required_fields(self):
        required = (
            'a',
            'b',
        )

        config = {
            'a': 6,
            'b': 'foo',
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

    def test_build_missing_required_field(self):
        required = (
            'a',
            'b',
        )

        config = {
            'a': 6,
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
            'extra': "will be ignored",
            'd': {
                'e': 'bar'
            }
        }

        test_class = ConfigBuilder.build(
            default_config={},
            required_config=(),
            config_constructor=TestConfigBuilderAssets.constructor,
            config=config
        )

        self.assertIsInstance(test_class, TestConfigBuilderAssets.TestClass)
        self.assertEqual(test_class.a, config['a'])
        self.assertEqual(test_class.b, config['b'])


class TestConfigBuilderAssets:
    class TestClass(NamedTuple):
        a: int
        b: str

    @classmethod
    def constructor(cls, d: Dict):
        return TestConfigBuilderAssets.TestClass(d['a'], d['b'])
