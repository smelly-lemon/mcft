from __future__ import annotations

import pytest
from pydantic import BaseModel, ValidationError

from mcft.schemas import (
    CheckerKind,
    Episode,
    EvalResult,
    EvalTask,
    ExecutionResult,
    GameState,
    Message,
    Outcome,
    Provenance,
    SFTExample,
    SFTSource,
    Split,
    StepType,
    TaskCategory,
    TrajectoryStep,
    utc_now,
)

_GAME_STATE = GameState(
    position=(1.0, 64.0, -3.5),
    health=20.0,
    hunger=18.0,
    time_of_day="day",
    inventory={"oak_log": 4},
    nearby_entities=["zombie"],
)

_TRAJECTORY_STEP = TrajectoryStep(
    episode_id="ep1",
    step_index=0,
    timestamp=utc_now(),
    step_type=StepType.COMMAND,
    persona_id="sable",
    system_prompt_hash="ab" * 32,
    game_state=_GAME_STATE,
    model_input="collect wood",
    model_output='!collectBlocks("oak_log", 10)',
    thinking_mode=True,
    deliberation_trigger="action_planning",
    thinking="Need wood first.",
    parsed_command="collectBlocks",
    execution_result=ExecutionResult(ok=True, message=None),
    latency_ms=412.5,
    reward_signals={"progress": 0.1},
)

INSTANCES: list[BaseModel] = [
    _GAME_STATE,
    ExecutionResult(ok=False, message="no path"),
    _TRAJECTORY_STEP,
    Episode(
        started_at=utc_now(),
        ended_at=utc_now(),
        mindcraft_version="0.1.4",
        model_id="mock",
        persona_id="sable",
        task_id="collect_wood",
        outcome=Outcome.SUCCESS,
        steps_path="data/raw/episodes/ep1/steps.jsonl",
    ),
    Message(role="assistant", content="Scoping the area."),
    Provenance(
        teacher_model="Qwen3.5-35B-A3B",
        license="Apache-2.0",
        source_episode_id="ep1",
        pipeline_version="v0",
        generated_at=utc_now(),
    ),
    SFTExample(
        messages=[Message(role="user", content="hi"), Message(role="assistant", content="Hello.")],
        persona_id="sable",
        thinking_mode=False,
        source=SFTSource.TRAJECTORY,
        provenance=Provenance(generated_at=utc_now()),
        split=Split.TRAIN,
    ),
    EvalTask(
        id="collect_wood",
        name="Collect wood",
        description="Punch/chop trees until logs are gathered.",
        category=TaskCategory.GATHER,
        success_criteria="inventory contains >= 10 logs of any type",
        checker=CheckerKind.PROGRAMMATIC,
        max_steps=40,
        seeds=[10, 23, 33, 41, 54],
    ),
    EvalResult(
        task_id="collect_wood",
        model_id="mock",
        persona_id="sable",
        seed=10,
        success=False,
        steps_used=10,
        wall_time_s=1.2,
        latency_p50_ms=400.0,
        latency_p95_ms=650.0,
        syntax_error_count=0,
        persona_adherence=None,
        transcript_path=None,
    ),
]


@pytest.mark.parametrize("instance", INSTANCES, ids=lambda i: type(i).__name__)
def test_schema_roundtrip(instance: BaseModel) -> None:
    restored = type(instance).model_validate_json(instance.model_dump_json())
    assert restored == instance


def test_strict_models_reject_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        TrajectoryStep(
            **_TRAJECTORY_STEP.model_dump(),
            bogus_field="nope",
        )
    state = GameState(bogus_field="fine")
    assert state.model_extra == {"bogus_field": "fine"}
