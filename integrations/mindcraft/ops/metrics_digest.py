"""Hourly metrics digest over mcft trajectory logs.

Appends one JSON line per run to metrics/digest.jsonl and rewrites
metrics/digest.txt with a human-readable table of recent windows. Stdlib
only; run on the Studio by digest_daemon.sh.

Window: the last 6 hours of steps (rolling), plus cumulative totals.
"""

from __future__ import annotations

import glob
import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Studio runs Python 3.9; datetime.UTC arrived in 3.11
UTC = timezone.utc  # noqa: UP017

MINDCRAFT = Path.home() / "Desktop" / "mindcraft"
EPISODES = MINDCRAFT / "data" / "raw" / "episodes"
OUT_DIR = MINDCRAFT / "metrics"

WINDOW_H = 6
TOP_COMMANDS = ["!placeHere", "!goToCoordinates", "!collectBlocks", "!craftRecipe", "!givePlayer"]


def load_steps() -> list[dict]:
    steps = []
    for f in glob.glob(str(EPISODES / "*" / "steps.jsonl")):
        prev_out = None
        for line in open(f, encoding="utf-8"):
            try:
                s = json.loads(line)
            except json.JSONDecodeError:
                continue
            s["_repeat"] = s.get("model_output") == prev_out
            prev_out = s.get("model_output")
            steps.append(s)
    return steps


def summarize(steps: list[dict]) -> dict:
    n = len(steps)
    uses, fails = Counter(), Counter()
    for s in steps:
        cmd, er = s.get("parsed_command"), s.get("execution_result")
        if cmd and er:
            uses[cmd] += 1
            if not er.get("ok"):
                fails[cmd] += 1
    lat = sorted(s.get("latency_ms", 0) for s in steps if s.get("latency_ms", 0) > 0)
    chat = sum(1 for s in steps if s.get("step_type") == "chat")
    out: dict = {
        "steps": n,
        "chat_pct": round(100 * chat / n, 1) if n else 0.0,
        "repeats_per_1k": round(1000 * sum(s["_repeat"] for s in steps) / n, 1) if n else 0.0,
        "latency_p50_s": round(lat[len(lat) // 2] / 1000, 1) if lat else None,
        "latency_p95_s": round(lat[int(len(lat) * 0.95)] / 1000, 1) if lat else None,
    }
    for cmd in TOP_COMMANDS:
        u, f = uses[cmd], fails[cmd]
        out[cmd] = {"uses": u, "fails": f, "fail_pct": round(100 * f / u, 1) if u else None}
    return out


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    steps = load_steps()
    now = datetime.now(UTC)
    cutoff = now - timedelta(hours=WINDOW_H)
    recent = [s for s in steps if datetime.fromisoformat(s["timestamp"]) >= cutoff]

    record = {
        "at": now.isoformat(timespec="seconds"),
        "window_h": WINDOW_H,
        "recent": summarize(recent),
        "cumulative": summarize(steps),
    }
    with (OUT_DIR / "digest.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")

    # human-readable rolling table (last 12 records)
    records = [
        json.loads(line) for line in (OUT_DIR / "digest.jsonl").open(encoding="utf-8")
    ][-12:]
    lines = [
        f"mcft metrics digest (rolling {WINDOW_H}h windows; regenerated "
        f"{now.strftime('%Y-%m-%d %H:%M UTC')})",
        "",
        f"{'when (UTC)':<17} {'steps':>6} {'chat%':>6} {'rep/1k':>7} {'p50s':>5} "
        f"{'place%':>7} {'goto%':>6} {'collect%':>9} {'craft%':>7} {'give%':>6}",
    ]
    def pct(window: dict, cmd: str) -> str:
        v = window[cmd]["fail_pct"]
        return "-" if v is None else f"{v:.0f}"

    for r in records:
        w = r["recent"]
        lines.append(
            f"{r['at'][5:16]:<17} {w['steps']:>6} {w['chat_pct']:>6} "
            f"{w['repeats_per_1k']:>7} {w['latency_p50_s'] or '-':>5} "
            f"{pct(w, '!placeHere'):>7} {pct(w, '!goToCoordinates'):>6} "
            f"{pct(w, '!collectBlocks'):>9} {pct(w, '!craftRecipe'):>7} {pct(w, '!givePlayer'):>6}"
        )
    (OUT_DIR / "digest.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"digest written: {record['recent']['steps']} steps in window")


if __name__ == "__main__":
    main()
