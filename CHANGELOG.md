# Changelog

All notable changes to jsonmend are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project aims to
follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] — 2026-11-01

First release.

### Added
- `mend()` — a tolerant reader that turns almost-JSON into a Python value: looks
  past prose and Markdown fences; accepts single/curly quotes, unquoted keys,
  trailing/leading/missing commas, `//` and `/* */` comments, and Python
  literals; reads lenient numbers; maps `NaN`/`Infinity` to `null`; and closes a
  truncated stream so it still parses.
- `repair()` — the same, returning clean JSON text (with `indent`, `sort_keys`,
  `ensure_ascii`).
- `loads()` — a `json.loads`-shaped alias.
- A JSON Schema **subset** (`validate()`): `type`, `enum`, `const`,
  `properties`, `required`, `additionalProperties: false`, `items`, `default`,
  numeric bounds, and string/array length — with optional scalar **coercion**
  and **default**-filling.
- A `jsonmend` command-line tool (stdin or file, `--schema`, `--compact`, and
  documented exit codes), also runnable as `python -m jsonmend`.
