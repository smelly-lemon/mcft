"""Integration test: battery checkers against the LIVE eval server (no bots).

Stages a known arena state via RCON (wall, chest with items), then asserts
the real checker stack reads it correctly through the same code path the
battery runner will use. Requires the eval server up on tim4:25577.

Usage: uv run python integrations/mindcraft/ops/checker_integration_test.py <rcon_password>
"""

from __future__ import annotations

import sys

from mcft.evals.battery import CheckerSpec
from mcft.evals.live import CheckerContext, Rcon, evaluate_checker

HOST, PORT = "tim4", 25577
AX, AY, AZ = 1000, 100, 1000


def main() -> None:
    rcon = Rcon(HOST, PORT, sys.argv[1])
    ctx = CheckerContext(bot="NoSuchBot", ax=AX, ay=AY, az=AZ)
    run = rcon.cmd

    # stage arena
    run(f"forceload add {AX - 16} {AZ - 16} {AX + 16} {AZ + 16}")
    run(f"fill {AX - 2} {AY - 1} {AZ - 2} {AX + 8} {AY - 1} {AZ + 8} stone")
    run(f"fill {AX} {AY} {AZ} {AX + 4} {AY + 2} {AZ} cobblestone")
    run(f"setblock {AX} {AY} {AZ + 2} chest")
    run(f"item replace block {AX} {AY} {AZ + 2} container.0 with cobblestone 32")

    wall = {
        "region": {
            "from": ["{ax}", "{ay}", "{az}"],
            "to": ["{ax+4}", "{ay+2}", "{az}"],
            "block": "cobblestone",
        }
    }

    failed = 0

    def check(name: str, spec: CheckerSpec, expected: bool) -> None:
        # evaluate immediately: staged world state changes between phases
        nonlocal failed
        got = evaluate_checker(spec, ctx, run)
        if got != expected:
            failed += 1
        print(f"{'ok  ' if got == expected else 'FAIL'} {name}: got {got}, expected {expected}")

    check(
        "full wall scan",
        CheckerSpec(kind="block_region_scan", params={**wall, "min_fraction": 1.0}),
        True,
    )
    check(
        "chest has 32 cobble",
        CheckerSpec(
            kind="chest_contains",
            params={"x": "{ax}", "y": "{ay}", "z": "{az+2}",
                    "item_pattern": "cobblestone", "count": 32},
        ),
        True,
    )
    check(
        "chest lacks 33",
        CheckerSpec(
            kind="chest_contains",
            params={"x": "{ax}", "y": "{ay}", "z": "{az+2}",
                    "item_pattern": "cobblestone", "count": 33},
        ),
        False,
    )
    check(
        "missing entity is False, not error",
        CheckerSpec(
            kind="position_within",
            params={"x": "{ax}", "y": "{ay}", "z": "{az}", "radius": 10},
        ),
        False,
    )

    # knock 6 blocks out -> 9/15 = 0.60: passes 0.34, fails 0.67
    run(f"fill {AX} {AY + 2} {AZ} {AX + 4} {AY + 2} {AZ} air")
    run(f"setblock {AX + 4} {AY + 1} {AZ} air")
    check(
        "partial wall passes 0.34",
        CheckerSpec(kind="block_region_scan", params={**wall, "min_fraction": 0.34}),
        True,
    )
    check(
        "partial wall fails 0.67",
        CheckerSpec(kind="block_region_scan", params={**wall, "min_fraction": 0.67}),
        False,
    )

    # teardown
    run(f"fill {AX - 2} {AY - 1} {AZ - 2} {AX + 8} {AY + 2} {AZ + 8} air")
    run("forceload remove all")
    rcon.close()
    print("ALL OK" if not failed else f"{failed} FAILURES")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
