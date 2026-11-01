"""The repair engine: a small, forgiving JSON reader.

Rather than patch the text with a pile of regular expressions (which tends to
break on the next odd input), jsonmend *reads* the text the way a lenient human
would and builds a normal Python value. Re-emitting that value with
:func:`json.dumps` yields clean, strict JSON.

The reader tolerates, in one pass:

* prose or chatter before and after the value ("Sure! Here you go: {...}"),
* Markdown code fences (``` ```json … ``` ```),
* single quotes, "smart" curly quotes, and unquoted object keys,
* trailing, leading and duplicated commas, and missing commas,
* ``//`` and ``/* … */`` comments,
* Python's ``True`` / ``False`` / ``None`` and bare unquoted string values,
* and a stream cut off by a token limit — any structure still open at the end
  of the text is simply closed.
"""

from __future__ import annotations

import json
import re
from typing import Any

__all__ = ["mend", "repair", "loads", "MendError", "RepairError"]


class MendError(ValueError):
    """Base class for every jsonmend failure."""


class RepairError(MendError):
    """The input could not be read as JSON, even generously.

    ``pos`` is the index into the candidate text where the reader gave up, when
    that is known.
    """

    def __init__(self, message: str, *, pos: int | None = None) -> None:
        super().__init__(message)
        self.pos = pos


_WS = " \t\r\n\f\v   "
# Opening string delimiter -> the delimiters that may legally close it. Smart
# quotes may be closed by their curly partner or by the straight equivalent.
_QUOTES: dict[str, tuple[str, ...]] = {
    '"': ('"',),
    "'": ("'",),
    "“": ("”", '"'),  # “ ”
    "”": ("”", '"'),
    "‘": ("’", "'"),  # ‘ ’
    "’": ("’", "'"),
}
_SIMPLE_ESCAPES = {
    '"': '"', "\\": "\\", "/": "/",
    "b": "\b", "f": "\f", "n": "\n", "r": "\r", "t": "\t",
}
_HEX = set("0123456789abcdefABCDEF")
_FENCE_RE = re.compile(r"```[^\n`]*\n(.*?)```", re.DOTALL)


class _Reader:
    """A forgiving recursive-descent reader over a single JSON value."""

    def __init__(self, src: str) -> None:
        self.s = src
        self.n = len(src)
        self.i = 0
        self.truncated = False  # set when the end of input forced a structure closed

    # -- scanning helpers -------------------------------------------------
    def _skip_trivia(self) -> None:
        """Advance past whitespace and ``//`` / ``/* */`` comments."""
        s, n = self.s, self.n
        while self.i < n:
            c = s[self.i]
            if c in _WS:
                self.i += 1
            elif c == "/" and self.i + 1 < n and s[self.i + 1] == "/":
                nl = self.i + 2
                while nl < n and s[nl] not in "\r\n":
                    nl += 1
                self.i = nl
            elif c == "/" and self.i + 1 < n and s[self.i + 1] == "*":
                end = s.find("*/", self.i + 2)
                self.i = end + 2 if end != -1 else n
            else:
                break

    # -- entry ------------------------------------------------------------
    def read_document(self) -> Any:
        start = self._find_value_start()
        if start is None:
            raise RepairError("no JSON value found in input", pos=0)
        self.i = start
        return self._value()

    def _find_value_start(self) -> int | None:
        """Index of where the value begins, skipping any leading prose/fences.

        An object or array is what models are almost always asked for, so the
        first ``{`` or ``[`` wins; failing that, the first string/number/literal.
        """
        s, n = self.s, self.n
        low = s.lower()
        fallback: int | None = None
        for idx in range(n):
            c = s[idx]
            if c in "{[":
                return idx
            if fallback is not None:
                continue
            if c in _QUOTES or c.isdigit():
                fallback = idx
            elif c in "+-." and idx + 1 < n and (s[idx + 1].isdigit() or s[idx + 1] == "."):
                fallback = idx
            elif low.startswith(("true", "false", "null"), idx):
                # a real literal, not the start of a longer word like "nullable"
                end = idx + (5 if low.startswith("false", idx) else 4)
                after = s[end] if end < n else " "
                if not (after.isalnum() or after == "_"):
                    fallback = idx
        return fallback

    # -- values -----------------------------------------------------------
    def _value(self) -> Any:
        self._skip_trivia()
        if self.i >= self.n:
            self.truncated = True
            return None
        c = self.s[self.i]
        if c == "{":
            return self._object()
        if c == "[":
            return self._array()
        if c in _QUOTES:
            return self._string()
        if c in "+-":
            nxt = self.s[self.i + 1] if self.i + 1 < self.n else ""
            if nxt.isdigit() or nxt == ".":
                return self._number()
        elif c.isdigit() or c == ".":
            return self._number()
        return self._bareword_value()

    def _object(self) -> dict:
        self.i += 1  # past {
        obj: dict[str, Any] = {}
        s = self.s
        while True:
            self._skip_trivia()
            if self.i >= self.n:
                self.truncated = True
                return obj
            c = s[self.i]
            if c == "}":
                self.i += 1
                return obj
            if c == ",":
                self.i += 1  # tolerate leading / doubled commas
                continue
            mark = self.i
            key = self._key()
            self._skip_trivia()
            if self.i < self.n and s[self.i] == ":":
                self.i += 1  # the usual case
            value = self._value()
            obj[key] = value
            self._skip_trivia()
            if self.i < self.n and s[self.i] == ",":
                self.i += 1
            if self.i <= mark:  # safety: never spin on an unconsumable char
                self.i = mark + 1

    def _array(self) -> list:
        self.i += 1  # past [
        arr: list[Any] = []
        s = self.s
        while True:
            self._skip_trivia()
            if self.i >= self.n:
                self.truncated = True
                return arr
            c = s[self.i]
            if c == "]":
                self.i += 1
                return arr
            if c == ",":
                self.i += 1
                continue
            mark = self.i
            arr.append(self._value())
            self._skip_trivia()
            if self.i < self.n and s[self.i] == ",":
                self.i += 1
            if self.i <= mark:
                self.i = mark + 1

    def _key(self) -> str:
        self._skip_trivia()
        if self.i < self.n and self.s[self.i] in _QUOTES:
            return self._string()
        s, n = self.s, self.n
        start = self.i
        while self.i < n and s[self.i] not in ":,{}[]" and s[self.i] not in _WS:
            self.i += 1
        return s[start:self.i]

    def _string(self) -> str:
        s, n = self.s, self.n
        quote = s[self.i]
        closers = _QUOTES.get(quote, (quote,))
        self.i += 1
        out: list[str] = []
        while self.i < n:
            c = s[self.i]
            if c == "\\":
                self.i += 1
                if self.i >= n:
                    break  # dangling backslash at end of input
                out.append(self._unescape(s[self.i]))
                self.i += 1
                continue
            if c in closers:
                self.i += 1
                return "".join(out)
            out.append(c)
            self.i += 1
        # reached end of input without a closing quote
        self.truncated = True
        return "".join(out)

    def _unescape(self, e: str) -> str:
        if e in _SIMPLE_ESCAPES:
            return _SIMPLE_ESCAPES[e]
        if e == "u":
            hexd = self.s[self.i + 1:self.i + 5]
            if len(hexd) == 4 and all(ch in _HEX for ch in hexd):
                self.i += 4
                return chr(int(hexd, 16))
            return "u"  # malformed \u escape: keep a literal u
        return e  # unknown escape (e.g. \') -> keep the character

    def _number(self) -> Any:
        s, n = self.s, self.n
        start = self.i
        if self.i < n and s[self.i] in "+-":
            self.i += 1
        while self.i < n and (s[self.i].isdigit() or s[self.i] == "_"):
            self.i += 1
        if self.i < n and s[self.i] == ".":
            self.i += 1
            while self.i < n and (s[self.i].isdigit() or s[self.i] == "_"):
                self.i += 1
        if self.i < n and s[self.i] in "eE":
            j = self.i + 1
            if j < n and s[j] in "+-":
                j += 1
            if j < n and s[j].isdigit():
                self.i = j + 1
                while self.i < n and s[self.i].isdigit():
                    self.i += 1
        raw = s[start:self.i].replace("_", "").lstrip("+")
        try:
            return float(raw) if any(ch in raw for ch in ".eE") else int(raw)
        except ValueError:
            return None

    def _bareword_value(self) -> Any:
        """An unquoted token in value position: a literal, or a bare string."""
        s, n = self.s, self.n
        start = self.i
        while self.i < n and s[self.i] not in ",:{}[]\r\n":
            self.i += 1
        word = s[start:self.i].strip()
        low = word.lower()
        if low == "true":
            return True
        if low == "false":
            return False
        if low in ("null", "none", "nil", "undefined", ""):
            return None
        if low in ("nan", "inf", "-inf", "infinity", "-infinity", "+infinity"):
            return None  # not representable in JSON; null keeps the output valid
        return word  # a bare, unquoted string value


def _fenced_blocks(text: str) -> list[str]:
    """Contents of any Markdown ``` fenced code blocks, in order."""
    return [m.group(1) for m in _FENCE_RE.finditer(text)]


def _reject_constant(token: str) -> Any:
    # json.loads is lenient about NaN/Infinity; we are not, so they fall through
    # to the tolerant reader, which maps non-finite values to null (valid JSON).
    raise ValueError(f"non-finite constant {token!r}")


def _strict_loads(text: str) -> Any:
    return json.loads(text, parse_constant=_reject_constant)


def _read(text: str) -> tuple[Any, bool]:
    """Return ``(value, truncated)`` for *text*, trying the cheapest route first."""
    stripped = text.strip()
    if stripped:
        try:
            return _strict_loads(stripped), False
        except ValueError:  # JSONDecodeError, or a rejected NaN/Infinity
            pass
    fenced = _fenced_blocks(text)
    for block in fenced:
        try:
            return _strict_loads(block.strip()), False
        except ValueError:
            pass
    last: RepairError | None = None
    for candidate in [*fenced, text]:
        reader = _Reader(candidate)
        try:
            return reader.read_document(), reader.truncated
        except RepairError as err:
            last = err
    raise last or RepairError("no JSON value found in input")


def mend(
    text: str,
    *,
    schema: dict | None = None,
    coerce: bool = True,
    defaults: bool = True,
) -> Any:
    """Read *text* as JSON, generously, and return the Python value.

    If *schema* (a JSON Schema ``dict``) is given, the result is validated
    against it; with *coerce* (default on) scalar types are nudged to fit
    (``"3"`` -> ``3`` where the schema says ``integer``), and with *defaults*
    (default on) missing object properties that declare a ``default`` are
    filled in. Raises :class:`RepairError` if nothing JSON-like can be read, or
    :class:`~jsonmend.schema.SchemaError` if the schema is not satisfied.
    """
    if not isinstance(text, str):
        raise TypeError(f"mend() expected str, got {type(text).__name__}")
    value, _truncated = _read(text)
    if schema is not None:
        from .schema import validate

        value = validate(value, schema, coerce=coerce, defaults=defaults)
    return value


def repair(
    text: str,
    *,
    schema: dict | None = None,
    coerce: bool = True,
    defaults: bool = True,
    indent: int | None = None,
    sort_keys: bool = False,
    ensure_ascii: bool = False,
) -> str:
    """Like :func:`mend`, but return clean JSON *text* instead of a Python value."""
    value = mend(text, schema=schema, coerce=coerce, defaults=defaults)
    return json.dumps(value, indent=indent, sort_keys=sort_keys, ensure_ascii=ensure_ascii)


def loads(text: str, **kwargs: Any) -> Any:
    """Alias for :func:`mend`, for a ``json.loads``-shaped call site."""
    return mend(text, **kwargs)
