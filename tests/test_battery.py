from __future__ import annotations

from pathlib import Path

import pytest

from mcft.evals.battery import (
    Battery,
    BatteryTask,
    CheckerSpec,
    Milestone,
    load_battery,
    score_episode,
)

SMOKE = Path("src/mcft/evals/tasks/battery_v1_smoke.yaml")


def _task(**overrides) -> dict:
    base = {
        "id": "t",
        "name": "T",
        "dimension": "execution",
        "goal_prompt": "do the thing",
        "budget_minutes": 10,
        "milestones": [
            {
                "id": "m1",
                "weight": 1.0,
                "checker": {
                    "kind": "inventory_at_least",
                    "params": {"item_pattern": "_log", "count": 10},
                },
            }
        ],
    }
    base.update(overrides)
    return base


def test_smoke_battery_loads_and_covers_dimensions() -> None:
    battery = load_battery(SMOKE)
    assert battery.version == 1
    assert len(battery.tasks) == 6
    dims = {t.dimension for t in battery.tasks}
    assert dims == {"execution", "long_horizon", "unstuck", "cooperation"}
    assert sum(t.pair for t in battery.tasks) == 1
    # every unstuck task carries its perturbation
    for task in battery.tasks:
        if task.dimension == "unstuck":
            assert task.perturbations


def test_milestone_weights_must_sum_to_one() -> None:
    bad = _task()
    bad["milestones"][0]["weight"] = 0.5
    with pytest.raises(ValueError, match="sum"):
        BatteryTask.model_validate(bad)


def test_checker_params_validated() -> None:
    with pytest.raises(ValueError, match="missing params"):
        CheckerSpec(kind="inventory_at_least", params={"count": 3})
    with pytest.raises(ValueError, match="region"):
        CheckerSpec(kind="block_region_scan", params={})
    ok = CheckerSpec(
        kind="block_region_scan",
        params={"region": {"from": [0, 0, 0], "to": [4, 2, 0], "block": "cobblestone"}},
    )
    assert ok.params["region"]["block"] == "cobblestone"


def test_unstuck_requires_perturbation() -> None:
    bad = _task(dimension="unstuck")
    with pytest.raises(ValueError, match="perturbation"):
        BatteryTask.model_validate(bad)


def test_duplicate_task_ids_rejected() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        Battery.model_validate({"version": 1, "tasks": [_task(), _task()]})


def test_score_episode_graded_credit() -> None:
    task = BatteryTask.model_validate(
        _task(
            milestones=[
                {
                    "id": "a",
                    "weight": 0.3,
                    "checker": {
                        "kind": "inventory_at_least",
                        "params": {"item_pattern": "x", "count": 1},
                    },
                },
                {
                    "id": "b",
                    "weight": 0.7,
                    "checker": {
                        "kind": "position_within",
                        "params": {"x": 0, "y": 64, "z": 0, "radius": 5},
                    },
                },
            ]
        )
    )
    assert score_episode(task, set()) == 0.0
    assert score_episode(task, {"a"}) == 0.3
    assert score_episode(task, {"a", "b"}) == 1.0
    with pytest.raises(ValueError, match="unknown"):
        score_episode(task, {"nope"})


def test_smoke_scores_are_computable() -> None:
    battery = load_battery(SMOKE)
    for task in battery.tasks:
        all_ids = {m.id for m in task.milestones}
        assert score_episode(task, all_ids) == pytest.approx(1.0)


def test_milestone_model_shape() -> None:
    m = Milestone(
        id="m",
        weight=1.0,
        checker=CheckerSpec(
            kind="chest_contains",
            params={"x": 0, "y": 64, "z": 2, "item_pattern": "cobblestone", "count": 32},
        ),
    )
    assert m.checker.kind == "chest_contains"