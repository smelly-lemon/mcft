"""Score a pulled ablation run: era-E arm vs era-F arm, side by side.

Reads the run directory produced by ops/ablation_runner.py (pull it first:
scp -r tim@tim4:Desktop/mindcraft/ablation/run-* analysis/runs/), computes
the shared meters per arm, and adds intent-graph stats for the F arm
(goal ops attempted/accepted, steps carrying an intent path).

Usage: uv run python analysis/ablation_score.py analysis/runs/run-20260721-1400
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

from mcft.evals.meters import Meters, compute_meters

SITE = (0, 86, 64)
GOAL_OPS = ("!goalDone", "!goalAdd", "!goalSwitch")


def arm_steps_files(run_dir: Path, arm: str) -> list[Path]:
    files = []
    for ep_dir in sorted(run_dir.glob(f"{arm}[0-9]*")):
        files.extend(sorted(ep_dir.glob("*/steps.jsonl")))
    return files


def intent_stats(files: list[Path]) -> dict:
    ops: Counter[str] = Counter()
    with_path = total = 0
    for fp in files:
        for line in fp.open():
            try:
                s = json.loads(line)
            except json.JSONDecodeError:
                continue
            total += 1
            if s.get("intent_path"):
                with_path += 1
            cmd = s.get("parsed_command") or ""
            for op in GOAL_OPS:
                if cmd.startswith(op):
                    ops[op] += 1
    return {
        "goal_ops": dict(ops),
        "intent_path_share": round(with_path / total, 3) if total else 0.0,
    }


def main() -> None:
    run_dir = Path(sys.argv[1])
    arms: dict[str, Meters] = {}
    for arm in ("E", "F"):
        files = arm_steps_files(run_dir, arm)
        if not files:
            print(f"warning: no steps for arm {arm}")
            continue
        arms[arm] = compute_meters(files, site=SITE)

    fields = [
        ("steps", "steps"),
        ("wall min", "wall_minutes"),
        ("command rate", "command_rate"),
        ("fail rate", "fail_rate"),
        ("invalid names", "invalid_name_rate"),
        ("repeat/1k", "repeat_per_1k"),
        ("alt/1k", "alternate_per_1k"),
        ("site p95 dist", "site_p95_distance"),
        ("deep share", "deep_step_share"),
        ("chest share", "chest_transfer_share"),
        ("chat share", "chat_share"),
        ("lat p50 s", "latency_p50_s"),
        ("lat p95 s", "latency_p95_s"),
    ]
    header = f"{'meter':<16}" + "".join(f"{a:>10}" for a in arms)
    print(header)
    print("-" * len(header))
    for label, attr in fields:
        row = f"{label:<16}"
        for m in arms.values():
            row += f"{getattr(m, attr):>10}"
        print(row)

    for arm, m in arms.items():
        print(f"\narm {arm} top command fails:")
        for name, (uses, fails) in m.command_fails.items():
            if fails:
                print(f"  {name:<18} {fails}/{uses} ({fails / uses:.0%})")

    if "F" in arms:
        stats = intent_stats(arm_steps_files(run_dir, "F"))
        print(
            f"\narm F intent: path on {stats['intent_path_share']:.0%} of steps, "
            f"goal ops {stats['goal_ops'] or 'none'}"
        )

    # journal drift check: GOAL line should be a mission phase. Arm F writes
    # graph node titles ("finish the house walls"), arm E the bare phase name.
    phase = re.compile(r"GOAL:.*\b(walls|roof|door|farm|improvements?)\b", re.I)
    for jf in sorted(run_dir.glob("*/journal_*.json")):
        mem = json.loads(jf.read_text()).get("memory", "")
        goal = re.search(r"GOAL:.*", mem)
        ok = "ok " if phase.search(mem) else "DRIFT"
        print(f"{ok} {jf.parent.name}/{jf.stem}: {goal.group(0)[:70] if goal else 'NO GOAL LINE'}")


if __name__ == "__main__":
    main()
