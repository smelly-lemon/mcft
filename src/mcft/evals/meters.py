"""Passive per-episode meters (docs/eval-battery-design.md).

Computed from steps.jsonl alone - no live server needed - so the same code
scores ablation arms, battery episodes, and wild soak corpora. Every meter
maps to an observed failure class from the wild corpus.
"""

from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path

from pydantic import Field

from mcft.schemas import StrictModel

TRANSFER_CHEST = ("!putInChest", "!takeFromChest")
TRANSFER_DIRECT = ("!givePlayer",)


class Meters(StrictModel):
    steps: int = 0
    wall_minutes: float = 0.0

    # protocol
    command_rate: float = 0.0  # steps with a parsed command
    empty_response_rate: float = 0.0
    invalid_name_rate: float = 0.0  # "not a valid"/"unknown" execution messages

    # stability
    fail_rate: float = 0.0  # failed / commanded steps
    repeat_per_1k: float = 0.0  # exact consecutive repeats (period 1)
    alternate_per_1k: float = 0.0  # ABAB (period 2)

    # discipline (site-relative; zeros when site unknown)
    site_p95_distance: float = 0.0
    deep_step_share: float = 0.0  # share of steps >10 blocks below site y

    # economy
    chat_share: float = 0.0
    chest_transfer_share: float = 0.0  # chest ops / (chest ops + givePlayer)

    # ops
    latency_p50_s: float = 0.0
    latency_p95_s: float = 0.0

    command_fails: dict[str, tuple[int, int]] = Field(default_factory=dict)  # name -> (uses, fails)


def _percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, math.ceil(q * len(ordered)) - 1))
    return ordered[idx]


def compute_meters(
    steps_files: list[Path] | list[str],
    site: tuple[int, int, int] | None = None,
) -> Meters:
    steps: list[dict] = []
    for fp in steps_files:
        with open(fp, encoding="utf-8") as fh:
            for line in fh:
                try:
                    steps.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    if not steps:
        return Meters()
    steps.sort(key=lambda s: s.get("timestamp") or "")

    n = len(steps)
    commanded = [s for s in steps if s.get("parsed_command")]
    latencies = [s["latency_ms"] / 1000 for s in steps if s.get("latency_ms")]

    uses: Counter[str] = Counter()
    fails: Counter[str] = Counter()
    invalid = 0
    for s in commanded:
        name = s["parsed_command"].split("(")[0]
        uses[name] += 1
        er = s.get("execution_result") or {}
        if er and not er.get("ok"):
            fails[name] += 1
            msg = (er.get("message") or "").lower()
            if "not a valid" in msg or "unknown" in msg or "did you mean" in msg:
                invalid += 1

    # repetition per bot (period 1 and 2 on exact model_output)
    rep = alt = 0
    history: dict[str, list[str]] = {}
    for s in steps:
        out = s.get("model_output") or ""
        h = history.setdefault(s.get("persona_id", "?"), [])
        if h and out == h[-1]:
            rep += 1
        elif len(h) >= 2 and out == h[-2] and out != h[-1]:
            alt += 1
        h.append(out)
        del h[:-3]

    # timestamps -> wall minutes
    ts = [s["timestamp"] for s in steps if s.get("timestamp")]
    wall_minutes = 0.0
    if len(ts) >= 2:
        from datetime import datetime

        def parse(t: str) -> datetime:
            return datetime.fromisoformat(t.replace("Z", "+00:00"))

        wall_minutes = (parse(ts[-1]) - parse(ts[0])).total_seconds() / 60

    dists: list[float] = []
    deep = 0
    if site is not None:
        sx, sy, sz = site
        for s in steps:
            pos = (s.get("game_state") or {}).get("position")
            if not pos:
                continue
            dists.append(math.sqrt((pos[0] - sx) ** 2 + (pos[2] - sz) ** 2))
            if pos[1] < sy - 10:
                deep += 1

    chest_ops = sum(uses[c] for c in TRANSFER_CHEST)
    direct_ops = sum(uses[c] for c in TRANSFER_DIRECT)
    transfers = chest_ops + direct_ops

    return Meters(
        steps=n,
        wall_minutes=round(wall_minutes, 1),
        command_rate=round(len(commanded) / n, 3),
        empty_response_rate=round(
            sum(1 for s in steps if not (s.get("model_output") or "").strip()) / n, 3
        ),
        invalid_name_rate=round(invalid / max(len(commanded), 1), 3),
        fail_rate=round(sum(fails.values()) / max(len(commanded), 1), 3),
        repeat_per_1k=round(1000 * rep / n, 1),
        alternate_per_1k=round(1000 * alt / n, 1),
        site_p95_distance=round(_percentile(dists, 0.95), 1),
        deep_step_share=round(deep / max(len(dists), 1), 3),
        chat_share=round(sum(1 for s in steps if s.get("step_type") == "chat") / n, 3),
        chest_transfer_share=round(chest_ops / transfers, 3) if transfers else 0.0,
        latency_p50_s=round(_percentile(latencies, 0.50), 1),
        latency_p95_s=round(_percentile(latencies, 0.95), 1),
        command_fails={name: (uses[name], fails.get(name, 0)) for name, _ in uses.most_common(12)},
    )
