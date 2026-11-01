"""Command line: ``jsonmend [FILE]`` reads almost-JSON and prints clean JSON.

    $ some-llm-call | jsonmend
    $ jsonmend reply.txt --schema action.schema.json --compact

Exit status: ``0`` on success, ``1`` if the input can't be read as JSON or
fails the schema, ``2`` for a bad invocation (e.g. an unreadable schema file).
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Sequence

from . import __version__
from .mend import MendError, repair


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="jsonmend",
        description="Repair almost-JSON from a language model into valid JSON.",
    )
    p.add_argument("file", nargs="?", help="input file (default: read standard input)")
    p.add_argument("-s", "--schema", metavar="FILE", help="JSON Schema to validate and coerce against")
    p.add_argument("--no-coerce", action="store_true", help="do not coerce scalar types to the schema")
    p.add_argument("--no-defaults", action="store_true", help="do not fill in schema defaults")
    p.add_argument("-c", "--compact", action="store_true", help="print on one line, no indentation")
    p.add_argument("-i", "--indent", type=int, default=2, metavar="N", help="indent width (default: 2)")
    p.add_argument("--sort-keys", action="store_true", help="sort object keys in the output")
    p.add_argument("--ascii", action="store_true", help="escape non-ASCII characters in the output")
    p.add_argument("-q", "--quiet", action="store_true", help="suppress error messages on stderr")
    p.add_argument("-V", "--version", action="version", version=f"jsonmend {__version__}")
    return p


def _read_input(path: str | None) -> str:
    if path is None or path == "-":
        return sys.stdin.read()
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    try:
        text = _read_input(args.file)
    except OSError as err:
        if not args.quiet:
            print(f"jsonmend: cannot read input: {err}", file=sys.stderr)
        return 2

    schema = None
    if args.schema:
        try:
            with open(args.schema, encoding="utf-8") as handle:
                schema = json.load(handle)
        except (OSError, json.JSONDecodeError) as err:
            if not args.quiet:
                print(f"jsonmend: cannot read schema {args.schema!r}: {err}", file=sys.stderr)
            return 2

    try:
        out = repair(
            text,
            schema=schema,
            coerce=not args.no_coerce,
            defaults=not args.no_defaults,
            indent=None if args.compact else args.indent,
            sort_keys=args.sort_keys,
            ensure_ascii=args.ascii,
        )
    except MendError as err:
        if not args.quiet:
            print(f"jsonmend: {err}", file=sys.stderr)
        return 1

    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
