"""Soft-reset bot cognition: seed fresh journals + re-issue the site goal.

Keeps the world and the site anchor; wipes short-term history and the
drifted journals (2026-07-18: bots invented an unbounded "extend roof"
project 45 blocks east of site). Seeds memory.json so each bot wakes with
a clean site-anchored plan, and rewrites settings.js init_message with
finish-line semantics (the old "keep improving it" bred infinite projects).

Run on the Studio with the Mindcraft stack STOPPED (agents write
memory.json on shutdown and would clobber the seeds).
"""

from __future__ import annotations

import json
import time
from pathlib import Path

MC = Path.home() / "Desktop" / "mindcraft"

GOAL = (
    "TEAM homestead at site (95, 85, -283) - permanent, never relocate. "
    "MISSION: finish the ONE house AT the site - complete walls, flat roof, "
    "and a door - then build a small wheat farm within 10 blocks of it. "
    "After the farm, improve the homestead (torches, fences, decorations) "
    "under the same rules. HARD RULES: never build anything more than 20 "
    "blocks from the site; never build paths or roads; if you are over 30 "
    "blocks from the site or underground, stop and return to (95, 85, -283) "
    "first. Check your journal SITE and GOAL lines before every plan. Use "
    "!startConversation to split roles - one gathers, one builds."
)

JOURNAL = """SITE: (95, 85, -283)
GOAL: Finish the ONE house at SITE (walls + flat roof + door), then a wheat farm within 10 blocks of it. Never build >20 blocks from SITE.
PLAN: 1. Go to SITE. 2. Survey the house: list wall gaps, missing roof, door. 3. Patch walls. 4. Lay flat roof. 5. Fit door. 6. Build farm.
NEXT: !goToCoordinates(95, 85, -283, 3)
NOTES: Soft reset 2026-07-18. The long slab path far EAST of SITE is ABANDONED - never return to it or extend it. Role split: {role}."""

ROLES = {
    "Sable": "Sable builds at SITE, Jolt gathers and delivers",
    "Jolt": "Jolt gathers logs/materials and delivers to Sable at SITE",
}


def seed_memories() -> None:
    for name, role in ROLES.items():
        fp = MC / "bots" / name / "memory.json"
        data = {
            "memory": JOURNAL.format(role=role),
            "turns": [],
            "self_prompting_state": 0,  # STOPPED; init_message re-issues !goal
            "self_prompt": None,
            "taskStart": int(time.time() * 1000),
            "last_sender": None,  # must be null so init_message fires on spawn
        }
        fp.write_text(json.dumps(data, indent=4), encoding="utf-8")
        print(f"seeded {fp}")


def update_init_message() -> None:
    settings = MC / "settings.js"
    lines = settings.read_text(encoding="utf-8").split("\n")
    inner = (
        "Begin now by responding with exactly this command and nothing else: "
        f"!goal({json.dumps(GOAL)})"
    )
    for i, ln in enumerate(lines):
        if ln.strip().startswith('"init_message":'):
            lines[i] = f'    "init_message": {json.dumps(inner)}, // sends to all on spawn'
            break
    else:
        raise AssertionError("init_message line not found")
    settings.write_text("\n".join(lines), encoding="utf-8")
    print("updated settings.js init_message")


if __name__ == "__main__":
    seed_memories()
    update_init_message()
