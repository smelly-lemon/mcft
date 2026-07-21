from __future__ import annotations

import pytest

from mcft.evals.battery import CheckerSpec
from mcft.evals.live import CheckerContext, evaluate_checker, substitute
from mcft.evals.live.substitute import resolve_int

CTX = CheckerContext(bot="Sable", ax=100, ay=64, az=-200)


def test_substitute_grammar() -> None:
    assert substitute("tp {bot} {ax+8} {ay-2} {az}", "Jolt", 10, 64, -5) == "tp Jolt 18 62 -5"
    assert substitute("no placeholders", "J", 0, 0, 0) == "no placeholders"
    with pytest.raises(ValueError, match="offset"):
        substitute("{bot+1}", "J", 0, 0, 0)


def test_resolve_int() -> None:
    assert resolve_int("{ay-3}", "J", 0, 86, 0) == 83
    assert resolve_int(42, "J", 0, 0, 0) == 42
    with pytest.raises(TypeError):
        resolve_int(1.5, "J", 0, 0, 0)


INVENTORY_NBT = (
    "Sable has the following entity data: [{count: 32, Slot: 0b, "
    'id: "minecraft:cobblestone"}, {count: 5, Slot: 1b, id: "minecraft:birch_log"}, '
    '{count: 7, Slot: 2b, id: "minecraft:oak_log"}]'
)


def _fake_runner(responses: dict[str, str]):
    def run(cmd: str) -> str:
        for key, value in responses.items():
            if key in cmd:
                return value
        return ""
    return run


def test_inventory_at_least_pattern_sums_across_variants() -> None:
    spec = CheckerSpec(kind="inventory_at_least", params={"item_pattern": "_log", "count": 12})
    run = _fake_runner({"data get entity Sable Inventory": INVENTORY_NBT})
    assert evaluate_checker(spec, CTX, run)
    spec_high = CheckerSpec(
        kind="inventory_at_least", params={"item_pattern": "_log", "count": 13}
    )
    assert not evaluate_checker(spec_high, CTX, run)


def test_chest_contains_uses_resolved_coords() -> None:
    spec = CheckerSpec(
        kind="chest_contains",
        params={"x": "{ax}", "y": "{ay}", "z": "{az+2}", "item_pattern": "cobblestone",
                "count": 32},
    )
    seen: list[str] = []

    def run(cmd: str) -> str:
        seen.append(cmd)
        return '[{count: 32, Slot: 0b, id: "minecraft:cobblestone"}]'

    assert evaluate_checker(spec, CTX, run)
    assert seen == ["data get block 100 64 -198 Items"]


def test_position_within_min_y_discriminates_pit() -> None:
    spec = CheckerSpec(
        kind="position_within",
        params={"x": "{ax+8}", "y": "{ay}", "z": "{az+8}", "radius": 40, "min_y": "{ay-1}"},
    )
    in_pit = _fake_runner({"Pos": "[108.5d, 62.0d, -192.5d]"})     # y=62 < min_y 63
    escaped = _fake_runner({"Pos": "[110.5d, 64.0d, -190.5d]"})
    assert not evaluate_checker(spec, CTX, in_pit)
    assert evaluate_checker(spec, CTX, escaped)


def test_block_region_scan_fraction() -> None:
    spec = CheckerSpec(
        kind="block_region_scan",
        params={
            "region": {"from": ["{ax}", "{ay}", "{az}"], "to": ["{ax+4}", "{ay+2}", "{az}"],
                       "block": "cobblestone"},
            "min_fraction": 0.34,
        },
    )
    filled = {f"execute if block {100 + dx} {64 + dy} -200": "Test passed"
              for dx in range(5) for dy in range(3) if dy == 0}

    def run(cmd: str) -> str:
        return next((v for k, v in filled.items() if cmd.startswith(k)), "Test failed")

    # bottom row only: 5/15 = 0.333... < 0.34 -> fail; add one block -> pass
    assert not evaluate_checker(spec, CTX, run)
    filled["execute if block 100 65 -200"] = "Test passed"
    assert evaluate_checker(spec, CTX, run)


def test_checker_never_raises_on_garbage() -> None:
    spec = CheckerSpec(
        kind="position_within", params={"x": 0, "y": 64, "z": 0, "radius": 5}
    )
    assert evaluate_checker(spec, CTX, lambda cmd: "no entity was found") is False

    def exploding(cmd: str) -> str:
        raise ConnectionError("server gone")

    assert evaluate_checker(spec, CTX, exploding) is False