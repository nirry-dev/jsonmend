"""Tests for the command-line interface."""

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout

from jsonmend.cli import main


def run(argv, stdin=""):
    """Run the CLI, returning (exit_code, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    real_stdin = __import__("sys").stdin
    __import__("sys").stdin = io.StringIO(stdin)
    try:
        with redirect_stdout(out), redirect_stderr(err):
            code = main(argv)
    finally:
        __import__("sys").stdin = real_stdin
    return code, out.getvalue(), err.getvalue()


class TestCli(unittest.TestCase):
    def test_stdin_repair(self):
        code, out, _ = run([], stdin="{'a': 1,}")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out), {"a": 1})

    def test_compact(self):
        code, out, _ = run(["--compact"], stdin='{"a": [1, 2]}')
        self.assertEqual(code, 0)
        self.assertEqual(out.strip(), '{"a": [1, 2]}')

    def test_file_input(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "reply.txt")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("```json\n{'ok': True}\n```")
            code, out, _ = run([path])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out), {"ok": True})

    def test_schema_file_coerces(self):
        with tempfile.TemporaryDirectory() as d:
            spath = os.path.join(d, "s.json")
            with open(spath, "w", encoding="utf-8") as fh:
                json.dump({"type": "object", "properties": {"n": {"type": "integer"}}}, fh)
            code, out, _ = run(["--schema", spath, "--compact"], stdin='{"n": "7"}')
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out), {"n": 7})

    def test_unreadable_input_is_exit_1(self):
        code, _, err = run([], stdin="just some prose, nothing to parse")
        self.assertEqual(code, 1)
        self.assertIn("jsonmend:", err)

    def test_bad_schema_file_is_exit_2(self):
        code, _, err = run(["--schema", "does-not-exist.json"], stdin="{}")
        self.assertEqual(code, 2)
        self.assertIn("schema", err)

    def test_quiet_suppresses_stderr(self):
        code, _, err = run(["--quiet"], stdin="nope")
        self.assertEqual(code, 1)
        self.assertEqual(err, "")


if __name__ == "__main__":
    unittest.main()
