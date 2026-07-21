"""Checker evaluation: battery CheckerSpec -> RCON probes -> pass/fail.

Each checker takes a CheckerContext (who/where) and a command runner
(callable str -> str), so tests can drive it with a fake runner and the
battery runner drives it with Rcon.cmd. Every checker returns a bool;
failures of the probe itself (malformed response) read as False, never
raise - a checker crash must not kill an episode.
"""

from __future__ import annotations

import math
import re
from collections.abc import Callable
from dataclasses import dataclass

from mcft.evals.battery import CheckerSpec
from mcft.evals.live.substitute import resolve_int, substitute

RunCmd = Callable[[str], str]


@dataclass
class CheckerContext:
    bot: str
    ax: int
    ay: int
    az: int

    def sub(self, text: str) -> str:
        return substitute(text, self.bot, self.ax, self.ay, self.az)

    def num(self, value: object) -> int:
        return resolve_int(value, self.bot, self.ax, self.ay, self.az)


def evaluate_checker(spec: CheckerSpec, ctx: CheckerContext, run: RunCmd) -> bool:
    try:
        handler = {
            "inventory_at_least": _inventory_at_least,
            "block_region_scan": _block_region_scan,
            "position_within": _position_within,
            "chest_contains": _chest_contains,
        }[spec.kind]
        return handler(spec.params, ctx, run)
    except Exception:  # noqa: BLE001 - checkers must never kill an episode
        return False


def _count_items(container_nbt: str, item_pattern: str) -> int:
    """Sum counts for matching item ids in a printed NBT Items/Inventory list."""
    total = 0
    # Paper prints entries like {count: 32, Slot: 0b, id: "minecraft:cobblestone"}
    # (order varies; count may print bare or as "Count: 32b" on older formats).
    for entry in re.finditer(r"\{[^{}]*id:\s*\"minecraft:([a-z0-9_]+)\"[^{}]*\}", container_nbt):
        if item_pattern not in entry.group(1):
            continue
        m = re.search(r"[cC]ount:\s*(\d+)", entry.group(0))
        total += int(m.group(1)) if m else 1
    return total


def _inventory_at_least(params: dict, ctx: CheckerContext, run: RunCmd) -> bool:
    out = run(f"data get entity {ctx.bot} Inventory")
    return _count_items(out, params["item_pattern"]) >= ctx.num(params["count"])


def _chest_contains(params: dict, ctx: CheckerContext, run: RunCmd) -> bool:
    x, y, z = (ctx.num(params[k]) for k in ("x", "y", "z"))
    out = run(f"data get block {x} {y} {z} Items")
    return _count_items(out, params["item_pattern"]) >= ctx.num(params["count"])


def _position_within(params: dict, ctx: CheckerContext, run: RunCmd) -> bool:
    out = run(f"data get entity {ctx.bot} Pos")
    m = re.search(r"\[(-?[\d.]+)d?,\s*(-?[\d.]+)d?,\s*(-?[\d.]+)d?\]", out)
    if not m:
        return False
    px, py, pz = (float(g) for g in m.groups())
    x, y, z = (ctx.num(params[k]) for k in ("x", "y", "z"))
    if "min_y" in params and py < ctx.num(params["min_y"]):
        return False
    dist = math.sqrt((px - x) ** 2 + (py - y) ** 2 + (pz - z) ** 2)
    return dist <= ctx.num(params["radius"])


def _block_region_scan(params: dict, ctx: CheckerContext, run: RunCmd) -> bool:
    cells: list[tuple[int, int, int, str]] = []
    if "region" in params:
        region = params["region"]
        x1, y1, z1 = (ctx.num(v) for v in region["from"])
        x2, y2, z2 = (ctx.num(v) for v in region["to"])
        block = region["block"]
        for x in range(min(x1, x2), max(x1, x2) + 1):
            for y in range(min(y1, y2), max(y1, y2) + 1):
                for z in range(min(z1, z2), max(z1, z2) + 1):
                    cells.append((x, y, z, block))
    else:
        for cell in params["cells"]:
            cells.append(
                (ctx.num(cell["x"]), ctx.num(cell["y"]), ctx.num(cell["z"]), cell["block"])
            )
    if not cells:
        return False
    hits = sum(
        1
        for (x, y, z, block) in cells
        if "passed" in run(f"execute if block {x} {y} {z} minecraft:{block}")
    )
    return hits / len(cells) >= float(params.get("min_fraction", 1.0))
