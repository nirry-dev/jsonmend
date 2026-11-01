"""Tests for the tolerant repair engine."""

import math
import unittest

import jsonmend
from jsonmend import RepairError, mend, repair


class TestValidPassthrough(unittest.TestCase):
    def test_already_valid(self):
        self.assertEqual(mend('{"a": 1, "b": [2, 3]}'), {"a": 1, "b": [2, 3]})

    def test_valid_scalar(self):
        self.assertEqual(mend("42"), 42)
        self.assertEqual(mend('"hi"'), "hi")
        self.assertIs(mend("true"), True)
        self.assertIsNone(mend("null"))


class TestFencesAndProse(unittest.TestCase):
    def test_json_fence(self):
        self.assertEqual(mend('```json\n{"a": 1}\n```'), {"a": 1})

    def test_bare_fence(self):
        self.assertEqual(mend("```\n[1, 2]\n```"), [1, 2])

    def test_prose_before_and_after(self):
        self.assertEqual(mend('Sure! Here you go:\n{"ok": true}\nHope that helps.'), {"ok": True})

    def test_prefers_object_over_earlier_number(self):
        self.assertEqual(mend("I found 3 results: {\"n\": 3}"), {"n": 3})

    def test_pure_prose_raises(self):
        for text in ("", "   ", "no json here", "nonetheless, information follows"):
            with self.assertRaises(RepairError):
                mend(text)


class TestLenientSyntax(unittest.TestCase):
    def test_trailing_comma_object(self):
        self.assertEqual(mend('{"a": 1,}'), {"a": 1})

    def test_trailing_comma_array(self):
        self.assertEqual(mend("[1, 2, 3,]"), [1, 2, 3])

    def test_single_quotes(self):
        self.assertEqual(mend("{'a': 'b'}"), {"a": "b"})

    def test_smart_quotes(self):
        self.assertEqual(mend("{“x”: “hi”}"), {"x": "hi"})

    def test_unquoted_keys(self):
        self.assertEqual(mend("{a: 1, b_2: 2}"), {"a": 1, "b_2": 2})

    def test_python_literals(self):
        self.assertEqual(mend('{"a": True, "b": False, "c": None}'), {"a": True, "b": False, "c": None})

    def test_line_comment(self):
        self.assertEqual(mend('{"a": 1 // a note\n, "b": 2}'), {"a": 1, "b": 2})

    def test_block_comment(self):
        self.assertEqual(mend('{/* lead */ "a": 1}'), {"a": 1})

    def test_missing_commas(self):
        self.assertEqual(mend('{"a": 1 "b": 2}'), {"a": 1, "b": 2})

    def test_unquoted_string_value(self):
        self.assertEqual(mend('{"status": ok}'), {"status": "ok"})


class TestTruncation(unittest.TestCase):
    def test_truncated_array(self):
        self.assertEqual(mend("[1, 2, 3"), [1, 2, 3])

    def test_truncated_object(self):
        self.assertEqual(mend('{"a": 1, "b": 2'), {"a": 1, "b": 2})

    def test_truncated_string(self):
        self.assertEqual(mend('{"msg": "hello wor'), {"msg": "hello wor"})

    def test_truncated_nested(self):
        self.assertEqual(mend('{"a": [1, {"b": 2'), {"a": [1, {"b": 2}]})


class TestNumbers(unittest.TestCase):
    def test_variety(self):
        self.assertEqual(
            mend("[1, -2, 3.5, 1e3, 1_000, .5, 5.]"),
            [1, -2, 3.5, 1000.0, 1000, 0.5, 5.0],
        )

    def test_non_finite_becomes_null(self):
        self.assertEqual(mend('{"x": NaN, "y": Infinity, "z": -Infinity}'), {"x": None, "y": None, "z": None})


class TestNesting(unittest.TestCase):
    def test_deep(self):
        text = "{'user': {'name': 'Mara', 'tags': ['a', 'b',], 'age': 30,}}"
        self.assertEqual(mend(text), {"user": {"name": "Mara", "tags": ["a", "b"], "age": 30}})


class TestRepairAndApi(unittest.TestCase):
    def test_repair_returns_text(self):
        self.assertEqual(repair("{'a': 1,}"), '{"a": 1}')

    def test_repair_indent(self):
        self.assertEqual(repair("[1]", indent=2), "[\n  1\n]")

    def test_loads_alias(self):
        self.assertEqual(jsonmend.loads("[true, false]"), [True, False])

    def test_non_string_raises_typeerror(self):
        with self.assertRaises(TypeError):
            mend({"already": "parsed"})  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
