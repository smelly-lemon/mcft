"""Placeholder substitution for battery specs.

Grammar (see battery.py): {bot}, {ax}/{ay}/{az} with optional integer
offsets like {ax+8} or {ay-2}. Values may be plain ints after substitution;
`resolve_int` coerces for checker params that arrive as placeholder strings.
"""

from __future__ import annotations

import re
from typing import Any

_PATTERN = re.compile(r"\{(bot|ax|ay|az)([+-]\d+)?\}")


def substitute(text: str, bot: str, ax: int, ay: int, az: int) -> str:
    values = {"ax": ax, "ay": ay, "az": az}

    def repl(m: re.Match[str]) -> str:
        name, offset = m.group(1), m.group(2)
        if name == "bot":
            if offset:
                raise ValueError(f"offset not allowed on {{bot}}: {m.group(0)}")
            return bot
        return str(values[name] + (int(offset) if offset else 0))

    return _PATTERN.sub(repl, text)


def resolve_int(value: Any, bot: str, ax: int, ay: int, az: int) -> int:
    if isinstance(value, bool):
        raise TypeError(f"expected int-like, got bool: {value!r}")
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return int(substitute(value, bot, ax, ay, az))
    raise TypeError(f"expected int or placeholder string, got {type(value).__name__}")
