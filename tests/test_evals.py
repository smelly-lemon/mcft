from __future__ import annotations

from pathlib import Path

from mcft.evals.client import MockClient
from mcft.evals.runner import DEFAULT_BATTERY, load_battery, run_matrix, write_results
from mcft.personas import ACTION_CONTRACT, load_all_personas
from mcft.schemas import CheckerKind, EvalResult, Message


def test_battery_loads() -> None:
    tasks = load_battery(DEFAULT_BATTERY)
    assert len(tasks) == 10
    for task in tasks:
        assert task.seeds == [10, 23, 33, 41, 54]
        assert isinstance(task.checker, CheckerKind)
    judge_tasks = [t.id for t in tasks if t.checker == CheckerKind.JUDGE]
    assert judge_tasks == ["build_shelter"]


def test_mock_client_deterministic() -> None:
    a, b = MockClient(seed=7), MockClient(seed=7)
    messages = [Message(role="user", content="go")]
    seq_a = [(r.content, r.latency_ms) for r in (a.chat(messages, model="mock") for _ in range(8))]
    seq_b = [(r.content, r.latency_ms) for r in (b.chat(messages, model="mock") for _ in range(8))]
    assert seq_a == seq_b


def _dry_run_results(persona_dir: Path) -> list[EvalResult]:
    personas_by_id = load_all_personas(persona_dir)
    personas = [personas_by_id["sable"], personas_by_id["jolt"]]
    return run_matrix(load_battery(DEFAULT_BATTERY), personas)


def test_runner_dry_run_totals(persona_dir: Path) -> None:
    results = _dry_run_results(persona_dir)
    assert len(results) == 100
    assert sum(r.success for r in results) == 80
    assert sum(r.syntax_error_count for r in results) == 40


def test_results_jsonl_roundtrip(persona_dir: Path, tmp_path: Path) -> None:
    results = _dry_run_results(persona_dir)
    results_path = write_results(results, tmp_path / "runs")
    lines = results_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == len(results)
    for line in lines:
        EvalResult.model_validate_json(line)


def test_packaged_resources_accessible() -> None:
    assert ACTION_CONTRACT
    tasks = load_battery(DEFAULT_BATTERY)
    assert len(tasks) == 10
