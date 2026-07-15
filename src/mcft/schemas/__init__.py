"""Core data models for mcft. Single source of truth for every pipeline stage.

Conventions: UTC timestamps, uuid4-hex ids, extra="forbid" everywhere except
GameState (extra="allow" for forward compatibility with the real logger).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


def new_id() -> str:
    return uuid.uuid4().hex


def utc_now() -> datetime:
    return datetime.now(UTC)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class StepType(StrEnum):
    CHAT = "chat"        # conversational output, no game effect
    COMMAND = "command"  # a !command invocation
    CODE = "code"        # newAction-style generated code
    SYSTEM = "system"    # framework-originated step (spawn, death, etc.)


class Outcome(StrEnum):
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    CRASHED = "crashed"


class SFTSource(StrEnum):
    TRAJECTORY = "trajectory"
    DISTILLED = "distilled"          # open-weight, permissively licensed teachers only (ADR-0003)
    SYNTHETIC_REWRITE = "synthetic_rewrite"


class Split(StrEnum):
    TRAIN = "train"
    VAL = "val"
    TEST = "test"                    # held-out episodes/tasks; never trained on


class TaskCategory(StrEnum):
    GATHER = "gather"
    CRAFT = "craft"
    BUILD = "build"
    SURVIVE = "survive"
    NAVIGATE = "navigate"


class CheckerKind(StrEnum):
    PROGRAMMATIC = "programmatic"    # computable from logged GameState/events (inventory, position, deaths)
    JUDGE = "judge"                  # judge model scores the trajectory log against the criteria
    MANUAL = "manual"                # operator reviews gameplay/logs by hand


class GameState(BaseModel):
    """Snapshot of world state at a step. extra='allow': the real Mindcraft
    logger may attach fields we haven't modeled yet without breaking parsing."""

    model_config = ConfigDict(extra="allow")

    position: tuple[float, float, float] | None = None
    health: float | None = None
    hunger: float | None = None
    time_of_day: str | None = None
    inventory: dict[str, int] = Field(default_factory=dict)
    nearby_entities: list[str] = Field(default_factory=list)


class ExecutionResult(StrictModel):
    ok: bool
    message: str | None = None


class TrajectoryStep(StrictModel):
    episode_id: str
    step_index: int
    timestamp: datetime
    step_type: StepType
    persona_id: str                 # per-step: personas can change mid-episode
    system_prompt_hash: str         # sha256 hex of the assembled system prompt
    game_state: GameState
    model_input: str
    model_output: str
    thinking_mode: bool             # SLOW (True) / FAST (False) requested for this step (ADR-0004);
                                    # distinct from thinking below, which may be empty even when requested
    deliberation_trigger: str | None = None  # what routed the mode: event type or escalation (ADR-0004)
    thinking: str | None = None     # captured reasoning content, if any
    parsed_command: str | None = None
    execution_result: ExecutionResult | None = None
    latency_ms: float
    reward_signals: dict[str, float] = Field(default_factory=dict)


class Episode(StrictModel):
    id: str = Field(default_factory=new_id)
    started_at: datetime
    ended_at: datetime | None = None
    mindcraft_version: str | None = None
    model_id: str
    persona_id: str                 # initial persona; per-step field is authoritative
    task_id: str | None = None
    outcome: Outcome | None = None
    steps_path: str                 # relative path to this episode's steps JSONL


class Message(StrictModel):
    role: Literal["system", "user", "assistant"]
    content: str


class Provenance(StrictModel):
    teacher_model: str | None = None       # None for organic trajectory data
    license: str | None = None
    source_episode_id: str | None = None   # lineage back to the originating episode
    pipeline_version: str | None = None    # datagen code/config version that produced this row
    generated_at: datetime


class SFTExample(StrictModel):
    id: str = Field(default_factory=new_id)
    messages: list[Message]
    persona_id: str
    thinking_mode: bool             # recorded request mode: SLOW (True) / FAST (False), copied from
                                    # the source TrajectoryStep (ADR-0004) — not inferred from content
    source: SFTSource
    provenance: Provenance
    split: Split


class EvalTask(StrictModel):
    id: str
    name: str
    description: str
    category: TaskCategory
    success_criteria: str           # declarative, human/judge-readable
    checker: CheckerKind            # how success_criteria gets decided (see §Real evaluation plan)
    max_steps: int
    seeds: list[int]


class EvalResult(StrictModel):
    task_id: str
    model_id: str
    persona_id: str
    seed: int
    success: bool
    steps_used: int
    wall_time_s: float
    latency_p50_ms: float
    latency_p95_ms: float
    syntax_error_count: int         # counted over command/code steps only
    persona_adherence: float | None = None   # judge-scored later; None in v0
    transcript_path: str | None = None
