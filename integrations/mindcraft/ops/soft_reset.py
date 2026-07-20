"""Soft-reset bot cognition: seed fresh journals + re-issue the site goal.

Wipes short-term history and journals, seeds a clean site-anchored plan
with the chest-first teamwork protocol, rewrites settings.js init_message
with mission-phase semantics, and writes mcft_site.json (consumed by the
siteguard patch in agent.js).

Run on the Studio with the Mindcraft stack STOPPED (agents write
memory.json on shutdown and would clobber the seeds).

Usage: python3 ops/soft_reset.py [--site X,Y,Z]
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

MC = Path.home() / "Desktop" / "mindcraft"

GOAL_TEMPLATE = (
    "TEAM homestead at site {site} - permanent, never relocate. MISSION "
    "PHASES IN ORDER: (1) finish the ONE house at the site - complete "
    "walls; (2) flat roof; (3) door; (4) small wheat farm within 10 blocks "
    "of the house; (5) improvements (torches, fences, decorations). Always "
    "work the earliest unfinished phase. HARD RULES: all construction "
    "within 20 blocks of the site; no paths, roads, or bridges; mining and "
    "gathering exist ONLY to feed the current phase - haul materials back "
    "as soon as you have what the phase needs; if you are over 30 blocks "
    "from the site or 10 blocks underground, return to the site first. "
    "TEAMWORK: transfer materials through the chest AT the site "
    "(!putInChest / !takeFromChest) and announce deposits in one short "
    "line; keep one bot gathering and one building; re-sync roles after "
    "any restart. Check your journal SITE and GOAL lines before every plan."
)

JOURNAL_TEMPLATE = """SITE: {site}
GOAL: house walls
PLAN: 1. Go to SITE. 2. Survey house: list wall gaps. 3. Gather/withdraw materials from site chest. 4. Close all wall gaps. 5. Then phase 2: roof.
NEXT: !goToCoordinates{site_call}
NOTES: Fresh start {date}. Mission phases: walls -> roof -> door -> wheat farm -> improvements. Chest at site = handoff point; announce deposits. Role: {role}."""

ROLES = {
    "Sable": "Sable builds at SITE; Jolt gathers and feeds the site chest",
    "Jolt": "Jolt gathers materials into the site chest; Sable builds",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", default="95,85,-283", help="X,Y,Z of home site")
    args = parser.parse_args()
    x, y, z = (int(v) for v in args.site.split(","))
    site = f"({x}, {y}, {z})"
    date = time.strftime("%Y-%m-%d")

    (MC / "mcft_site.json").write_text(
        json.dumps({"x": x, "y": y, "z": z}) + "\n", encoding="utf-8"
    )
    print(f"wrote mcft_site.json {site}")

    for name, role in ROLES.items():
        fp = MC / "bots" / name / "memory.json"
        fp.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "memory": JOURNAL_TEMPLATE.format(
                site=site, site_call=f"({x}, {y}, {z}, 3)", date=date, role=role
            ),
            "turns": [],
            "self_prompting_state": 0,  # STOPPED; init_message re-issues !goal
            "self_prompt": None,
            "taskStart": int(time.time() * 1000),
            "last_sender": None,  # must be null so init_message fires on spawn
        }
        fp.write_text(json.dumps(data, indent=4), encoding="utf-8")
        print(f"seeded {fp}")

    settings = MC / "settings.js"
    lines = settings.read_text(encoding="utf-8").split("\n")
    inner = (
        "Begin now by responding with exactly this command and nothing else: "
        f"!goal({json.dumps(GOAL_TEMPLATE.format(site=site))})"
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
    main()
