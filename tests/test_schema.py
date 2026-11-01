"""Tests for the JSON Schema subset: validation, coercion and defaults."""

import unittest

from jsonmend import SchemaError, mend, validate


class TestTypes(unittest.TestCase):
    def test_pass(self):
        validate({"n": 1}, {"type": "object", "properties": {"n": {"type": "integer"}}})

    def test_mismatch_raises(self):
        with self.assertRaises(SchemaError):
            validate("x", {"type": "integer"}, coerce=False)

    def test_union_type(self):
        validate(None, {"type": ["string", "null"]})
        validate("x", {"type": ["string", "null"]})

    def test_error_path(self):
        schema = {"type": "object", "properties": {"user": {"type": "object", "properties": {"age": {"type": "integer"}}}}}
        with self.assertRaises(SchemaError) as ctx:
            validate({"user": {"age": "old"}}, schema, coerce=False)
        self.assertEqual(ctx.exception.path, ".user.age")


class TestCoercion(unittest.TestCase):
    def test_str_to_int(self):
        self.assertEqual(validate("3", {"type": "integer"}), 3)

    def test_str_to_number(self):
        self.assertEqual(validate("1.5", {"type": "number"}), 1.5)

    def test_str_to_bool(self):
        self.assertIs(validate("true", {"type": "boolean"}), True)
        self.assertIs(validate("no", {"type": "boolean"}), False)

    def test_number_to_string(self):
        self.assertEqual(validate(7, {"type": "string"}), "7")

    def test_float_to_int(self):
        self.assertEqual(validate(4.0, {"type": "integer"}), 4)

    def test_no_coerce_flag(self):
        with self.assertRaises(SchemaError):
            validate("3", {"type": "integer"}, coerce=False)

    def test_end_to_end_with_mend(self):
        schema = {
            "type": "object",
            "properties": {"count": {"type": "integer"}, "live": {"type": "boolean"}},
        }
        self.assertEqual(mend('{"count": "5", "live": "yes"}', schema=schema), {"count": 5, "live": True})


class TestObjects(unittest.TestCase):
    def test_required_missing(self):
        with self.assertRaises(SchemaError):
            validate({"a": 1}, {"type": "object", "required": ["b"]})

    def test_defaults_filled(self):
        schema = {"type": "object", "properties": {"mode": {"default": "auto"}}}
        self.assertEqual(validate({}, schema), {"mode": "auto"})

    def test_defaults_off(self):
        schema = {"type": "object", "properties": {"mode": {"default": "auto"}}}
        self.assertEqual(validate({}, schema, defaults=False), {})

    def test_additional_properties_false(self):
        schema = {"type": "object", "properties": {"a": {}}, "additionalProperties": False}
        with self.assertRaises(SchemaError):
            validate({"a": 1, "b": 2}, schema)


class TestEnumsAndConst(unittest.TestCase):
    def test_enum_pass(self):
        validate("allow", {"enum": ["allow", "block"]})

    def test_enum_fail(self):
        with self.assertRaises(SchemaError):
            validate("maybe", {"enum": ["allow", "block"]})

    def test_const(self):
        validate("v1", {"const": "v1"})
        with self.assertRaises(SchemaError):
            validate("v2", {"const": "v1"})


class TestArraysAndBounds(unittest.TestCase):
    def test_items(self):
        self.assertEqual(validate(["1", "2"], {"type": "array", "items": {"type": "integer"}}), [1, 2])

    def test_min_items(self):
        with self.assertRaises(SchemaError):
            validate([1], {"type": "array", "minItems": 2})

    def test_number_bounds(self):
        validate(5, {"type": "integer", "minimum": 1, "maximum": 10})
        with self.assertRaises(SchemaError):
            validate(0, {"type": "integer", "minimum": 1})
        with self.assertRaises(SchemaError):
            validate(5, {"type": "integer", "exclusiveMaximum": 5})

    def test_string_length(self):
        with self.assertRaises(SchemaError):
            validate("abcd", {"type": "string", "maxLength": 3})


if __name__ == "__main__":
    unittest.main()
