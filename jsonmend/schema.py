"""A small, honest subset of JSON Schema — enough to hold model output to shape.

This is deliberately *not* a full JSON Schema implementation. It covers the
keywords that matter when you are coaxing structured output out of a language
model and want to fail loudly, or coerce quietly, when it drifts:

``type`` (incl. a list of types), ``enum``, ``const``, ``properties``,
``required``, ``additionalProperties`` (``False`` to forbid extras), ``items``,
``default``, and the common bounds ``minimum`` / ``maximum`` /
``exclusiveMinimum`` / ``exclusiveMaximum`` / ``minLength`` / ``maxLength`` /
``minItems`` / ``maxItems``.

With ``coerce`` on (the default), a scalar of the wrong type is nudged to fit
when it unambiguously can: ``"3"`` -> ``3`` for ``integer``, ``"true"`` ->
``True`` for ``boolean``, a number -> its string form for ``string``. With
``defaults`` on, a missing property that declares a ``default`` is filled in.
"""

from __future__ import annotations

import re
from typing import Any

from .mend import MendError

__all__ = ["validate", "SchemaError"]


class SchemaError(MendError):
    """The mended value did not satisfy the schema.

    ``path`` points at the offending location (``""`` is the root, ``.user.age``
    a nested property, ``[2]`` an array item).
    """

    def __init__(self, reason: str, *, path: str = "") -> None:
        super().__init__(f"{path or '<root>'}: {reason}")
        self.path = path
        self.reason = reason


_TYPE_CHECKS = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "null": lambda v: v is None,
}
_INT_RE = re.compile(r"[-+]?\d+")


def _type_name(value: Any) -> str:
    for name, check in _TYPE_CHECKS.items():
        if name not in ("number",) and check(value):
            return name
    if isinstance(value, float):
        return "number"
    return type(value).__name__


def _coerce(value: Any, types: list[str]) -> tuple[Any, bool]:
    """Try to turn *value* into one of *types*. Return ``(value, matched)``."""
    for t in types:
        if t == "integer" and not isinstance(value, bool):
            if isinstance(value, float) and value.is_integer():
                return int(value), True
            if isinstance(value, str) and _INT_RE.fullmatch(value.strip()):
                return int(value.strip()), True
        elif t == "number" and not isinstance(value, bool):
            if isinstance(value, int):
                return value, True
            if isinstance(value, str):
                try:
                    return float(value.strip()), True
                except ValueError:
                    pass
        elif t == "boolean":
            if isinstance(value, str):
                low = value.strip().lower()
                if low in ("true", "yes", "y", "on", "1"):
                    return True, True
                if low in ("false", "no", "n", "off", "0"):
                    return False, True
            elif isinstance(value, int) and value in (0, 1):
                return bool(value), True
        elif t == "string":
            if isinstance(value, bool):
                return ("true" if value else "false"), True
            if isinstance(value, (int, float)):
                return repr(value) if isinstance(value, float) else str(value), True
        elif t == "null":
            if isinstance(value, str) and value.strip().lower() in ("", "null", "none"):
                return None, True
    return value, False


def validate(
    value: Any,
    schema: dict,
    *,
    coerce: bool = True,
    defaults: bool = True,
    path: str = "",
) -> Any:
    """Validate *value* against *schema*; return the (possibly coerced) value."""
    if not isinstance(schema, dict) or not schema:
        return value

    types = schema.get("type")
    if types is not None:
        tlist = [types] if isinstance(types, str) else list(types)
        if not any(_TYPE_CHECKS.get(t, lambda v: True)(value) for t in tlist):
            if coerce:
                value, matched = _coerce(value, tlist)
            else:
                matched = False
            if not matched and not any(_TYPE_CHECKS.get(t, lambda v: True)(value) for t in tlist):
                raise SchemaError(f"expected {' or '.join(tlist)}, got {_type_name(value)}", path=path)

    if "const" in schema and value != schema["const"]:
        raise SchemaError(f"expected {schema['const']!r}", path=path)
    if "enum" in schema and value not in schema["enum"]:
        raise SchemaError(f"{value!r} is not one of {schema['enum']!r}", path=path)

    if isinstance(value, dict):
        props = schema.get("properties", {})
        if defaults:
            for key, sub in props.items():
                if key not in value and isinstance(sub, dict) and "default" in sub:
                    value[key] = sub["default"]
        for key in schema.get("required", []):
            if key not in value:
                raise SchemaError(f"missing required property {key!r}", path=path)
        extra = schema.get("additionalProperties", True)
        for key, item in list(value.items()):
            if key in props:
                value[key] = validate(
                    item, props[key], coerce=coerce, defaults=defaults, path=f"{path}.{key}"
                )
            elif extra is False:
                raise SchemaError(f"unexpected property {key!r}", path=path)

    if isinstance(value, list):
        items = schema.get("items")
        if isinstance(items, dict):
            value = [
                validate(item, items, coerce=coerce, defaults=defaults, path=f"{path}[{idx}]")
                for idx, item in enumerate(value)
            ]
        if "minItems" in schema and len(value) < schema["minItems"]:
            raise SchemaError(f"has {len(value)} items, needs at least {schema['minItems']}", path=path)
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            raise SchemaError(f"has {len(value)} items, allows at most {schema['maxItems']}", path=path)

    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            raise SchemaError(f"is shorter than {schema['minLength']} characters", path=path)
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            raise SchemaError(f"is longer than {schema['maxLength']} characters", path=path)

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            raise SchemaError(f"is below the minimum {schema['minimum']}", path=path)
        if "maximum" in schema and value > schema["maximum"]:
            raise SchemaError(f"is above the maximum {schema['maximum']}", path=path)
        if "exclusiveMinimum" in schema and value <= schema["exclusiveMinimum"]:
            raise SchemaError(f"must be greater than {schema['exclusiveMinimum']}", path=path)
        if "exclusiveMaximum" in schema and value >= schema["exclusiveMaximum"]:
            raise SchemaError(f"must be less than {schema['exclusiveMaximum']}", path=path)

    return value
