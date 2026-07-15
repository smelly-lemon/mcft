"""Eval runner: tasks x personas x seeds against an Environment.

Dry runs (the only mode in v0) wire MockClient + MockEnvironment. The dry
run validates schemas, wiring, determinism, and report formatting — it
measures nothing about model capability (success is seeded arithmetic).
"""

from __future__ import annotations

import argparse
import math
import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import yaml

from mcft.evals.client import ChatClient, MockClient
from mcft.personas import Persona, assemble_system_prompt, load_persona
from mcft.schemas import EvalResult, EvalTask, Message, new_id, utc_now

DEFAULT_BATTERY = Path(__file__).parent / "tasks" / "battery_v0.yaml"


@dataclass
class StepOutcome:
    observation: str
    done: bool
    success: bool
    syntax_error: bool


class Environment(Protocol):
    def reset(self, task: EvalTask, seed: int) -> str: ...  # initial observation
    def step(self, model_output: str) -> StepOutcome: ...


class MockEnvironment:
    """Canned determinism per (task, seed) — not a simulator."""

    def __init__(self) -> None:
        self._task: EvalTask | None = None
        self._seed = 0
        self._steps = 0
        self._will_succeed = False
        self._target_steps = 0

    def reset(self, task: EvalTask, seed: int) -> str:
        self._task = task
        self._seed = seed
        self._steps = 0
        self._will_succeed = seed % 5 != 0
        if self._will_succeed:
            self._target_steps = min(task.max_steps, 8 + (seed % 7))
        else:
            self._target_steps = min(task.max_steps, 10)
        return f"You spawn near a forest. Task: {task.name}."

    def step(self, model_output: str) -> StepOutcome:
        self._steps += 1
        done = self._steps >= self._target_steps
        return StepOutcome(
            observation=f"Step {self._steps} acknowledged.",
            done=done,
            success=self._will_succeed if done else False,
            syntax_error=(self._steps == 2 and self._seed % 3 == 0),
        )


def classify_is_command(model_output: str) -> bool:
    """Starts with '!' => command, else chat. Code classification arrives
    with real Mindcraft integration."""
    return model_output.startswith("!")


def load_battery(path: Path) -> list[EvalTask]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return [EvalTask.model_validate(t) for t in data["tasks"]]


def run_episode(
    task: EvalTask,
    persona: Persona,
    seed: int,
    client: ChatClient,
    env: Environment,
    model_id: str,
) -> EvalResult:
    system_prompt = assemble_system_prompt(persona, task.description)
    observation = env.reset(task, seed)
    history: list[Message] = []

    latencies: list[float] = []
    syntax_error_count = 0
    steps_used = 0
    start = time.perf_counter()

    for _ in range(task.max_steps):
        messages = (
            [Message(role="system", content=system_prompt)]
            + history
            + [Message(role="user", content=observation)]
        )
        response = client.chat(messages, model=model_id)
        latencies.append(response.latency_ms)
        outcome = env.step(response.content)
        steps_used += 1
        if classify_is_command(response.content) and outcome.syntax_error:
            syntax_error_count += 1
        history.append(Message(role="user", content=observation))
        history.append(Message(role="assistant", content=response.content))
        observation = outcome.observation
        if outcome.done:
            break

    wall_time_s = time.perf_counter() - start
    n = len(latencies)
    return EvalResult(
        task_id=task.id,
        model_id=model_id,
        persona_id=persona.id,
        seed=seed,
        success=outcome.success,
        steps_used=steps_used,
        wall_time_s=wall_time_s,
        latency_p50_ms=statistics.median(latencies),
        latency_p95_ms=sorted(latencies)[max(0, math.ceil(0.95 * n) - 1)],
        syntax_error_count=syntax_error_count,
    )


def run_matrix(
    tasks: list[EvalTask],
    personas: list[Persona],
    model_id: str = "mock",
) -> list[EvalResult]:
    results: list[EvalResult] = []
    env = MockEnvironment()
    for task in tasks:
        for persona in personas:
            for seed in task.seeds:
                client = MockClient(seed=seed)
                results.append(run_episode(task, persona, seed, client, env, model_id))
    return results


def write_results(results: list[EvalResult], out_dir: Path) -> Path:
    run_dir = out_dir / utc_now().strftime("%Y%m%d-%H%M%S")
    if run_dir.exists():
        run_dir = Path(f"{run_dir}-{new_id()[:6]}")
    run_dir.mkdir(parents=True)
    results_path = run_dir / "results.jsonl"
    with results_path.open("w", encoding="utf-8") as f:
        for result in results:
            f.write(result.model_dump_json() + "\n")
    return results_path


def print_summary(results: list[EvalResult], persona_order: list[str]) -> None:
    header = (
        f"{'task':<16} | {'persona':<8} | {'n':>3} | {'succ%':>6} | "
        f"{'mean_steps':>10} | {'p50ms':>7} | {'p95ms':>7} | {'syn':>4}"
    )
    print(header)
    print("-" * len(header))
    task_ids = list(dict.fromkeys(r.task_id for r in results))
    for task_id in task_ids:
        for persona_id in persona_order:
            group = [r for r in results if r.task_id == task_id and r.persona_id == persona_id]
            if not group:
                continue
            n = len(group)
            succ = 100.0 * sum(r.success for r in group) / n
            mean_steps = sum(r.steps_used for r in group) / n
            p50 = statistics.median(r.latency_p50_ms for r in group)
            p95 = statistics.median(r.latency_p95_ms for r in group)
            syn = sum(r.syntax_error_count for r in group)
            print(
                f"{task_id:<16} | {persona_id:<8} | {n:>3} | {succ:>5.1f}% | "
                f"{mean_steps:>10.1f} | {p50:>7.1f} | {p95:>7.1f} | {syn:>4}"
            )

    print()
    print("Persona rollup:")
    baseline_succ: float | None = None
    for persona_id in persona_order:
        group = [r for r in results if r.persona_id == persona_id]
        if not group:
            continue
        succ = 100.0 * sum(r.success for r in group) / len(group)
        if baseline_succ is None:
            baseline_succ = succ
            print(f"  {persona_id:<8} succ% {succ:>5.1f}  (baseline)")
        else:
            print(f"  {persona_id:<8} succ% {succ:>5.1f}  Δsucc% {succ - baseline_succ:>+5.1f}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="mcft eval runner")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--personas", default="sable,jolt")
    parser.add_argument("--persona-dir", default="configs/personas")
    parser.add_argument("--battery", default=str(DEFAULT_BATTERY))
    parser.add_argument("--out", default="runs/")
    args = parser.parse_args(argv)

    if not args.dry_run:
        print(
            "Only --dry-run is supported in v0 (real environments arrive with "
            "Mindcraft integration). Re-run with --dry-run."
        )
        return 2

    persona_dir = Path(args.persona_dir)
    persona_ids = [p.strip() for p in args.personas.split(",") if p.strip()]
    personas: list[Persona] = []
    for pid in persona_ids:
        path = persona_dir / f"{pid}.yaml"
        if not path.exists():
            print(f"Persona '{pid}' not found: no file at {path}. Check --persona-dir.")
            return 2
        personas.append(load_persona(path))

    tasks = load_battery(Path(args.battery))
    results = run_matrix(tasks, personas)
    results_path = write_results(results, Path(args.out))
    print(f"Wrote {len(results)} results to {results_path}\n")
    print_summary(results, persona_ids)
    return 0


if __name__ == "__main__":
    sys.exit(main())
