"""Battery v1 schema + scoring (docs/eval-battery-design.md).

Typed task specs for the live battery: dimensions, weighted milestones,
RCON setup/perturbation scripts, wall-clock budgets, pair flag. The runner
(Studio, Phase 4 step 3) consumes these; this module owns validation and
the scoring math so both are unit-tested offline.

Placeholder convention in RCON commands and goal prompts: {bot} = agent
name, {ax}/{ay}/{az} = arena origin, with simple integer offsets allowed
({ax+8}, {ay-2}). The runner substitutes at episode start.

Milestones LATCH: the runner polls checkers through the episode and a
milestone that passes once stays passed (e.g. "mined 32 cobble" must count
even after the cobble is deposited into the chest).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import Field, field_validator, model_validator

from mcft.schemas import StrictModel

Dimension = Literal["execution", "long_horizon", "unstuck", "cooperation"]

CHECKER_KINDS = (
    "inventory_at_least",   # bot inventory holds >= count of item_pattern
    "block_region_scan",    # % of spec cells matching expected block
    "position_within",      # bot within radius of a point
    "chest_contains",       # chest at coords holds >= count of item_pattern
)


class CheckerSpec(StrictModel):
    kind: Literal[
        "inventory_at_least", "block_region_scan", "position_within", "chest_contains"
    ]
    params: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _params_for_kind(self) -> CheckerSpec:
        required = {
            "inventory_at_least": {"item_pattern", "count"},
            # region: {from: [x,y,z], to: [x,y,z], block: name} (+ optional
            # min_fraction for graded scans); cells: explicit cell list.
            "block_region_scan": set(),
            "position_within": {"x", "y", "z", "radius"},  # optional min_y
            "chest_contains": {"x", "y", "z", "item_pattern", "count"},
        }[self.kind]
        missing = required - self.params.keys()
        if missing:
            raise ValueError(f"checker {self.kind} missing params: {sorted(missing)}")
        if self.kind == "block_region_scan" and not (
            "region" in self.params or "cells" in self.params
        ):
            raise ValueError("block_region_scan needs 'region' or 'cells'")
        return self


class Milestone(StrictModel):
    id: str
    weight: float = Field(gt=0)
    checker: CheckerSpec


class Perturbation(StrictModel):
    at_minutes: float = Field(gt=0)
    commands: list[str]  # RCON, with placeholders
    note: str = ""


class BatteryTask(StrictModel):
    id: str
    name: str
    dimension: Dimension
    goal_prompt: str  # verbatim goal handed to the bot(s)
    budget_minutes: float = Field(gt=0)
    pair: bool = False
    arena: Literal["flat", "natural"] = "natural"
    setup: list[str] = Field(default_factory=list)  # RCON, with placeholders
    perturbations: list[Perturbation] = Field(default_factory=list)
    milestones: list[Milestone]
    notes: str = ""

    @field_validator("milestones")
    @classmethod
    def _weights_sum_to_one(cls, v: list[Milestone]) -> list[Milestone]:
        total = sum(m.weight for m in v)
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"milestone weights sum to {total}, expected 1.0")
        ids = [m.id for m in v]
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate milestone ids")
        return v

    @model_validator(mode="after")
    def _unstuck_has_perturbation(self) -> BatteryTask:
        if self.dimension == "unstuck" and not self.perturbations:
            raise ValueError("unstuck tasks must define a perturbation")
        return self


class Battery(StrictModel):
    version: int
    tasks: list[BatteryTask]

    @field_validator("tasks")
    @classmethod
    def _unique_ids(cls, v: list[BatteryTask]) -> list[BatteryTask]:
        ids = [t.id for t in v]
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate task ids")
        return v


def load_battery(path: str | Path) -> Battery:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return Battery.model_validate(data)


def score_episode(task: BatteryTask, passed_milestones: set[str]) -> float:
    """Weighted-milestone sum in [0,1]; graded credit so weak models
    produce signal, not zeros."""
    known = {m.id for m in task.milestones}
    unknown = passed_milestones - known
    if unknown:
        raise ValueError(f"unknown milestones for {task.id}: {sorted(unknown)}")
    return round(sum(m.weight for m in task.milestones if m.id in passed_milestones), 6)
