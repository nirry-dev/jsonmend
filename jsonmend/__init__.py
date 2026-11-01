"""jsonmend — turn almost-JSON from a language model into valid JSON.

Models asked for JSON still wrap it in prose, fence it in Markdown, leave a
trailing comma, use single quotes, or get cut off mid-object by a token limit.
jsonmend reads that generously and hands back a normal Python value (or clean
JSON text), and can check and coerce it against a JSON Schema on the way out.

    >>> import jsonmend
    >>> jsonmend.mend('```json\\n{"ok": True, "n": 3,}\\n```')
    {'ok': True, 'n': 3}

Pure standard library, no runtime dependencies.
"""

from .mend import MendError, RepairError, loads, mend, repair
from .schema import SchemaError, validate

__version__ = "0.1.0"

__all__ = [
    "mend",
    "repair",
    "loads",
    "validate",
    "MendError",
    "RepairError",
    "SchemaError",
    "__version__",
]
