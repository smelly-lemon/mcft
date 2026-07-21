from __future__ import annotations

import json
from pathlib import Path

from mcft.evals.meters import Meters, compute_meters


def _step(
    i: int,
    bot: str = "sable",
    out: str = "x",
    cmd: str | None = None,
    ok: bool = True,
    pos: list[float] | None = None,
    latency: int = 10000,
) -> dict:
    return {
        "timestamp": f"2026-07-21T10:{i // 60:02d}:{i % 60:02d}",
        "persona_id": bot,
        "model_output": out,
        "parsed_command": cmd,
        "execution_result": None if cmd is None else {"ok": ok, "message": "" if ok else "failed"},
        "step_type": "command" if cmd else "chat",
        "latency_ms": latency,
        "game_state": {"position": pos or [0.0, 86.0, 64.0]},
    }


def _write(tmp_path: Path, steps: list[dict]) -> Path:
    fp = tmp_path / "steps.jsonl"
    fp.write_text("\n".join(json.dumps(s) for s in steps) + "\n")
    return fp


def test_empty_input() -> None:
    assert compute_meters([]) == Meters()


def test_basic_rates_and_latency(tmp_path: Path) -> None:
    steps = [
        _step(0, out="a", cmd='!collectBlocks("oak_log", 8)', ok=True, latency=8000),
        _step(10, out="b", cmd='!placeHere("dirt")', ok=False, latency=12000),
        _step(20, out="chat only", latency=16000),
    ]
    m = compute_meters([_write(tmp_path, steps)])
    assert m.steps == 3
    assert m.command_rate == round(2 / 3, 3)
    assert m.fail_rate == 0.5
    assert m.latency_p50_s == 12.0
    assert m.command_fails["!placeHere"] == (1, 1)


def test_repetition_and_alternation_per_bot(tmp_path: Path) -> None:
    repeats = [_step(i, bot="sable", out="same") for i in range(4)]  # 3 repeats
    # 6 ABAB turns -> 4 alternations
    alts = [_step(10 + i, bot="jolt", out=("A" if i % 2 == 0 else "B")) for i in range(6)]
    steps = repeats + alts
    m = compute_meters([_write(tmp_path, steps)])
    assert m.repeat_per_1k == round(1000 * 3 / 10, 1)
    assert m.alternate_per_1k == round(1000 * 4 / 10, 1)


def test_site_discipline(tmp_path: Path) -> None:
    steps = [
        _step(0, pos=[0.0, 86.0, 64.0]),
        _step(1, pos=[30.0, 86.0, 64.0]),  # 30 blocks out
        _step(2, pos=[0.0, 60.0, 64.0]),  # 26 below site y -> deep
    ]
    m = compute_meters([_write(tmp_path, steps)], site=(0, 86, 64))
    assert m.site_p95_distance == 30.0
    assert m.deep_step_share == round(1 / 3, 3)


def test_chest_transfer_share(tmp_path: Path) -> None:
    steps = [
        _step(0, cmd='!putInChest("plank", 8)'),
        _step(1, cmd='!takeFromChest("plank", 8)'),
        _step(2, cmd='!takeFromChest("plank", 8)'),
        _step(3, cmd='!givePlayer("Jolt", "plank", 8)'),
    ]
    m = compute_meters([_write(tmp_path, steps)])
    assert m.chest_transfer_share == 0.75


def test_wall_minutes(tmp_path: Path) -> None:
    steps = [_step(0), _step(600)]  # timestamps 10 minutes apart
    m = compute_meters([_write(tmp_path, steps)])
    assert m.wall_minutes == 10.0
