# Contributing to jsonmend

Thanks for taking a look. jsonmend is small on purpose, and the bar for new
behavior is a real, reproducible piece of model output that it mishandles.

## Ground rules

- **Standard library only.** No runtime dependencies, ever. The build backend
  (hatchling) is the only exception, and only at build time.
- **Every change comes with a test.** Found a string jsonmend mangles? Add it to
  `tests/` as a failing case first, then fix it.
- **Keep the reader honest.** Lenience is good; guessing is not. jsonmend must
  never invent data that wasn't in the input.

## Running the tests

```bash
python -m unittest discover -s tests -t .
```

No install needed — the tests import the package from the repo root.

## Scope

Good additions: a syntax quirk real models produce, a JSON Schema keyword that
earns its place for shaping output, a clearer error. Out of scope: becoming a
full JSON Schema validator, or a JSON5/YAML parser. See "What it is not" in the
README.

## Reporting bugs

Open an issue with the smallest input that reproduces it and the output you
expected. Security issues go to **info@nirry.net** instead — see
[SECURITY.md](SECURITY.md).
