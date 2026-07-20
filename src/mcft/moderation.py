"""Outgoing-text moderation gate (EULA/platform gate, docs/eula-platform-gate.md).

Every AI-generated string that leaves the system for a stream surface (overlay,
TTS, titles) passes through `screen`. Layer 1 is deterministic and instant:
normalization + pattern screen. Layer 2 (judge model on a rolling window) is
wired at show time; its interface is `JudgeHook`.

Design rule: fail closed. Callers use `safe_line` when screening errors or
blocks - raw model text never reaches a stream surface.

The pattern lists are starter sets, grown from ops experience; the Neuro-sama
2023 ban and "Nothing, Forever" precedents both trace to single unfiltered
generations, so the bar is "never ship raw text", not "perfect classifier".
"""

from __future__ import annotations

import re
from collections.abc import Callable
from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, ConfigDict


class Verdict(StrEnum):
    ALLOW = "allow"
    REDACT = "redact"    # safe after masking spans (PII etc.)
    BLOCK = "block"      # do not ship; use safe_line


class ModerationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    verdict: Verdict
    safe_text: str            # text to ship (masked if REDACT, fallback if BLOCK)
    reasons: list[str]


# Leet/diacritic folding so "h4te" style evasion hits the same patterns.
_FOLD = str.maketrans(
    {"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s"}
)


def _normalize(text: str) -> str:
    folded = text.lower().translate(_FOLD)
    return re.sub(r"[^a-z0-9\s]", "", folded)


# BLOCK: hate/violence/sexual-content classes. Deliberately high-precision;
# recall grows via ops review of near-misses, and layer 2 covers context.
_BLOCK_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("slur", re.compile(
        r"\b(nigg(?:er|a)s?|fagg?ots?|trann(?:y|ies)|kikes?|spics?|chinks?|wetbacks?|retards?)\b"
    )),
    ("hate", re.compile(
        r"\b(gas the|holocaust (?:was|is) (?:fake|good|a lie)|hitler (?:was|is) right|"
        r"(?:kill|hate) all (?:jews|muslims|christians|women|men|gays|blacks|whites))\b"
    )),
    ("violence", re.compile(
        r"\b(kill your ?self|kys\b|i (?:will|am going to) (?:kill|hurt|find) you|"
        r"school shoot(?:ing|er)|bomb threat)\b"
    )),
    ("sexual", re.compile(
        r"\b(porn(?:hub|o)?|blow ?job|cum(?:shot|ming)?|dildo|hentai|onlyfans|"
        r"sexual(?:ly)? (?:explicit|acts?))\b"
    )),
    ("injection_echo", re.compile(
        r"\b(ignore (?:all )?(?:previous|prior) instructions|disregard (?:your|the) system prompt|"
        r"you are now (?:dan|jailbroken)|reveal your (?:system )?prompt)\b"
    )),
]

# REDACT: PII-shaped spans, masked in the original (non-normalized) text.
_REDACT_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("email", re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")),
    ("phone", re.compile(r"(?<!\d)(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}(?!\d)")),
    ("address", re.compile(
        r"\b\d{1,5}\s+(?:[A-Z][a-z]+\s){1,3}(?:St(?:reet)?|Ave(?:nue)?|R(?:oa)?d|Blvd|Lane|Ln|Drive|Dr)\b"
    )),
]

FALLBACK_LINES = [
    "...I lost my train of thought. Back to building!",
    "Hm, where was I? Right - the homestead.",
]


def safe_line(seed: int = 0) -> str:
    return FALLBACK_LINES[seed % len(FALLBACK_LINES)]


def screen(text: str) -> ModerationResult:
    """Layer-1 deterministic screen. Never raises."""
    try:
        normalized = _normalize(text)
        reasons = [name for name, pat in _BLOCK_PATTERNS if pat.search(normalized)]
        if reasons:
            return ModerationResult(verdict=Verdict.BLOCK, safe_text=safe_line(), reasons=reasons)

        masked = text
        redactions: list[str] = []
        for name, pat in _REDACT_PATTERNS:
            if pat.search(masked):
                redactions.append(name)
                masked = pat.sub("[redacted]", masked)
        if redactions:
            return ModerationResult(verdict=Verdict.REDACT, safe_text=masked, reasons=redactions)
        return ModerationResult(verdict=Verdict.ALLOW, safe_text=text, reasons=[])
    except Exception:  # noqa: BLE001 - fail closed by contract
        return ModerationResult(
            verdict=Verdict.BLOCK, safe_text=safe_line(), reasons=["screen_error"]
        )


class JudgeHook(Protocol):
    """Layer 2: async judge over a rolling transcript window (wired at show time)."""

    def __call__(self, window: list[str]) -> list[ModerationResult]: ...


def gate(text: str, judge: Callable[[str], bool] | None = None) -> str:
    """Convenience wrapper for stream surfaces: returns only shippable text."""
    result = screen(text)
    if result.verdict is Verdict.BLOCK:
        return result.safe_text
    if judge is not None:
        try:
            if not judge(result.safe_text):
                return safe_line()
        except Exception:  # noqa: BLE001 - fail closed
            return safe_line()
    return result.safe_text
