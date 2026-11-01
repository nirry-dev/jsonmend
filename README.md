# jsonmend

**Turn almost-JSON from a language model into valid JSON.**

You asked a model for JSON. It gave you JSON — wrapped in a sentence, fenced in
Markdown, with a trailing comma, single quotes, and the last brace missing
because it hit the token limit. `jsonmend` reads that generously and hands back a
normal value, and can hold it to a JSON Schema on the way out.

```python
>>> import jsonmend
>>> jsonmend.mend('Sure! ```json\n{name: "Mara", tags: ["a", "b",], ok: True\n```')
{'name': 'Mara', 'tags': ['a', 'b'], 'ok': True}
```

No dependencies — just the Python standard library. Python 3.9+.

---

## Why

`json.loads` is strict on purpose, and it should stay that way for data you
control. Model output is not data you control: the same prompt returns clean
JSON nine times and something slightly off the tenth. `jsonmend` is the small,
auditable layer you put between a model and `json.loads` so that tenth response
doesn't take down the request.

It doesn't guess with regexes. It parses the text with a **forgiving reader** —
the way a patient human would — and rebuilds a real value, which it then emits
as strict JSON. One pass, no network, no model call, nothing to configure.

## Install

```bash
pip install jsonmend
```

Or vendor it: the `jsonmend/` package is pure standard library, so you can drop
it straight into a project with no build step.

## Use it

### In Python

```python
from jsonmend import mend, repair, loads

mend(text)                 # -> a Python value (dict / list / str / ... )
repair(text)               # -> clean JSON *text*
repair(text, indent=2)     # pretty-printed
loads(text)                # alias of mend(), for a json.loads-shaped call site
```

Hold the result to a shape with a JSON Schema — and let it coerce the near-misses:

```python
schema = {
    "type": "object",
    "required": ["action"],
    "properties": {
        "action": {"enum": ["draw", "write", "rest"]},
        "intensity": {"type": "integer", "minimum": 0, "maximum": 10, "default": 5},
        "urgent": {"type": "boolean"},
    },
}

mend('{"action": "draw", "intensity": "7", "urgent": "yes"}', schema=schema)
# {'action': 'draw', 'intensity': 7, 'urgent': True}
#            a string -> int ^^^           "yes" -> True ^^^   default filled if missing
```

A value that can't be read raises `RepairError`; one that can't be coerced to
the schema raises `SchemaError` with the exact `path` that failed.

### On the command line

```bash
some-llm-call | jsonmend                       # repaired JSON to stdout
jsonmend reply.txt --schema action.schema.json # validate + coerce against a schema
jsonmend reply.txt --compact                   # one line, no indentation
```

Exit status: `0` on success, `1` when the input can't be read or fails the
schema, `2` for a bad invocation (e.g. an unreadable schema file).

## What it forgives

In a single pass, the reader looks past or repairs:

- prose and chatter around the value — `Here you go: { … }`
- Markdown code fences — <code>```json … ```</code>
- single quotes, “smart” curly quotes, and unquoted object keys
- trailing, leading, doubled, and missing commas
- `//` line and `/* … */` block comments
- Python's `True` / `False` / `None`, and bare unquoted string values
- numbers with `_` separators, a leading `+`, or a bare leading/trailing dot
- `NaN` / `Infinity` → `null` (so the output stays valid JSON)
- **a truncated stream** — anything still open at the end of the text is closed,
  so a reply cut off by a token limit still parses as far as it got

## The JSON Schema it understands

A deliberate, honest **subset** — the keywords that matter when you're coaxing
structured output out of a model and want to fail loudly or coerce quietly:

`type` (and a list of types) · `enum` · `const` · `properties` · `required` ·
`additionalProperties: false` · `items` · `default` · `minimum` / `maximum` /
`exclusiveMinimum` / `exclusiveMaximum` · `minLength` / `maxLength` ·
`minItems` / `maxItems`.

Coercion (on by default) nudges a scalar to fit when it unambiguously can:
`"3" → 3`, `"1.5" → 1.5`, `"true"/"yes" → True`, a number → its string form, a
whole float → an int. Turn it off with `coerce=False` (CLI: `--no-coerce`), and
default-filling off with `defaults=False` (`--no-defaults`).

## What it is not

- **Not a replacement for a real JSON Schema validator.** For full Draft 2020-12
  validation on trusted data, use a dedicated library. jsonmend's subset is for
  shaping model output, not certifying documents.
- **Not a JSON5/YAML parser.** It is tolerant, not a different format.
- **Not a guesser.** It won't invent fields you didn't get. If a value truly
  isn't there, you get `null` (for a truncated stream) or an error — never a
  fabricated answer.

## License

MIT. Part of [Nirry Labs](https://nirry.net) — local-first AI and security
tools, dependency-light and auditable by design.
