# Kickoff: `mcft` — Steerable Minecraft Performance System

You are Claude, operating as a Cursor agent. This document lives at `kickoff_prompt.md` in the repo root and is the **source of truth**. Re-read it at the start of any session that references it. If it isn't yet committed, commit it first.

**Repo:** `github.com/smelly-lemon/mcft` (remote already created). Python package name: `mcft`.

The project: a **runtime-steerable Minecraft performance system** — an AI bot with distinct, audience-steerable personas, streamed live — with a fine-tuning pipeline as its engine. The show is the product; the model is infrastructure. Andy-4.2 (the community's free model) already covers "a decent local model plays Minecraft"; what does not exist anywhere is a persona show that paying viewers can steer, with measured reliability. That intersection is this project (see ADR-0007). Current session scope is **the pipeline scaffold only**: trajectory schema, persona system, eval harness — then (future sessions) the driver-powered show prototype, data generation, and training, in that order (see §Post-scaffold roadmap).

Product direction, recorded for context: first, stream the bot and sell viewer interactions (changing the bot's goals/persona through the ADR-0005 interaction loop); bot-hosting-as-a-service is undecided pending research; far future, possibly a fine-tuning-as-a-service platform where the moat is the tooling and UX, not the weights. Monetization stays out of build scope here; the architecture stays interoperable with it via ADR-0005. A Mojang EULA / Commercial Usage Guidelines go/no-go review is a hard gate before any monetization ships (see backlog).

**This session is scaffold + schemas + eval skeleton only.** No model downloads, no Mindcraft install, no network access beyond `git push`. Everything must run and pass tests on this laptop, offline.

**Execution rule for this document:** where exact code or file contents are given below, transcribe them verbatim. Where signatures or behavior are specified, implement to them exactly. Do not redesign, rename, or "improve." If something is genuinely ambiguous or broken, ask — don't invent.

---

## Architecture context (decided for now)

The positions below are working decisions, strong enough to build against. ADR-0002 (persona-conditioned SFT) and ADR-0004 (deliberation policy) are explicitly hypotheses to be validated by eval evidence, not settled facts — revisit them with data, never with vibes.

Three execution contexts, one repo:
- **Laptop (this machine):** development, tests, dry-run evals.
- **Mac Studio (M4 Max, 128GB):** production — local inference via llama.cpp `llama-server` (`--jinja`; Ollama/LM Studio as fallbacks — all behind the OpenAI-compatible client, so swapping is config), the 24/7 Mindcraft bot, trajectory logging, judge-model scoring.
- **RunPod (rented CUDA):** training only — Unsloth LoRA (bf16) → GGUF export → back onto the Studio.

Core principles:
1. **Capability lives in weights; personality lives at runtime.** Training data is persona-conditioned — organic per-persona trajectories first, chat-only rewrites as augmentation (see datagen README) — so system-prompt steering survives fine-tuning. Personas are config files. Runtime state (persona, goal) is mutable only through a single setter interface — the audience interaction loop, ADR-0005 — which is the product's core loop; payments later become just another caller of it.
2. **The trajectory schema is the keystone.** The logger writes it, datagen filters it, SFT formatting consumes it, evals score against it.
3. **Clean-room data provenance.** No Andy-model derivatives, no closed-API distillation. Every dataset row carries source metadata.
4. **Interface-driven model access.** All model calls go through an OpenAI-compatible chat-completions abstraction. Core code never imports provider SDKs. Everything runs against a mock.

## Known failure modes this design targets

Observed shortcomings of the existing community approach (Andy-4 / Mindcraft) and of naive versions of our plan, each mapped to a design element:

- **Persona collapse** — fine-tuning on one character's transcripts destroys steerability → persona-conditioned SFT; shared action-contract block; persona adherence as an eval metric.
- **Unmeasured steerability** — the Andy line already persona-conditions its training data (randomized names, varied persona prompts) but has never measured whether steering works → adherence scoring and per-persona deltas are the differentiator, not persona conditioning itself (ADR-0007).
- **No reproducible evaluation** → eval battery first; results as timestamped run artifacts with fixed seeds (kept out of git; `runs/` is gitignored — lineage lives in dataset/model hashes and model cards).
- **Mixed data provenance** → principle 3; `Provenance` on every `SFTExample`.
- **The reasoning tax** — a reasoning-distill base thinks before every utterance; a real-time bot can't afford that → per-step `latency_ms` and `thinking` capture; `thinking_mode` on SFT examples; latency percentiles in eval results; ADR-0004.
- **Undifferentiated steps** — chat, `!commands`, and `newAction` code are different behaviors with different metrics → `step_type` on every step; syntax-error rate computed on command/code steps only.
- **Success-only filtering strips recovery skill** — rejection sampling for clean wins removes recover-from-failure demonstrations → datagen policy keeps recovered-failure episodes (see datagen README below).
- **Training on the mistake itself** — keeping recovered-failure episodes naively makes the failure-causing step a training target, teaching the model to make the mistake → failed steps are context-only and never become assistant targets (loss-masked; see datagen README).
- **Capability degradation under persona** → eval matrix is tasks × seeds × personas with per-persona deltas.
- **Unsandboxed generated code** — a 24/7 bot executing `newAction` code is an arbitrary-code-execution surface → safety requirements in the Mindcraft integration README and ADR-0006.
- **Unbounded context growth in long sessions** → backlogged design item; the schema logs full `model_input` so we'll have the data to design it well.

## Stack and conventions

- Python **3.12**, `uv`, `pydantic` v2, `pytest`, `ruff`, `PyYAML`, `httpx`. **Stdlib is always allowed** (`statistics`, `random`, `uuid`, `hashlib`, `argparse`, etc.). No other dependencies without asking.
- `src/` layout, hatchling build backend. **Commit `uv.lock`** (do not gitignore it).
- Enums: `enum.StrEnum`. Timestamps: timezone-aware UTC `datetime`. IDs: `uuid.uuid4().hex` via the `new_id()` helper.
- All pydantic models use `extra="forbid"` except `GameState` (`extra="allow"`, forward-compatible).
- Type hints everywhere; no bare dicts crossing module boundaries.

## Repo layout

```
mcft/
├── kickoff_prompt.md          # this document
├── README.md
├── Makefile
├── pyproject.toml
├── uv.lock                    # committed
├── .gitignore
├── .env.example
├── src/mcft/
│   ├── __init__.py
│   ├── schemas/__init__.py    # all models, verbatim below
│   ├── personas/
│   │   ├── __init__.py        # loader + assemble_system_prompt
│   │   └── action_contract.txt
│   ├── evals/
│   │   ├── __init__.py
│   │   ├── client.py
│   │   ├── runner.py
│   │   └── tasks/battery_v0.yaml
│   └── datagen/README.md      # design doc only, content below
├── configs/personas/          # sable.yaml, jolt.yaml, herald.yaml
├── integrations/mindcraft/README.md
├── training/runpod/README.md
├── docs/
│   ├── decisions/             # ADR-0001..0007
│   ├── show-eval-v0.md        # entertainment scorecard (design)
│   ├── persona-design.md      # persona v1 spec (design)
│   └── backlog.md
└── tests/
```

## Session tasks (in order)

0. **Remote.** `git init`; add `origin` → `git@github.com:smelly-lemon/mcft.git` (HTTPS fallback if SSH isn't configured). Fetch; if the remote has an initial commit, pull it in before building. Commit `kickoff_prompt.md` at root. Push at end of session.
1. **Init.** Transcribe `pyproject.toml`, `Makefile`, `.gitignore`, `.env.example` from §Artifacts. `uv sync`.
2. **README.md.** Overview, three machine contexts, four principles, pointer to this file as source of truth, quickstart (`make setup && make test && make eval-dry`).
3. **Schemas.** Transcribe `src/mcft/schemas/__init__.py` verbatim from §Artifacts.
4. **Personas.** Transcribe `action_contract.txt` and the three persona YAMLs; implement loader + `assemble_system_prompt` to the spec in §Persona system.
5. **Evals.** Transcribe `battery_v0.yaml`; implement `client.py` and `runner.py` to the specs in §Eval harness.
6. **Stub READMEs.** Transcribe the datagen, training, and mindcraft README contents from §Artifacts.
7. **Decision log + design docs + backlog.** Transcribe ADR-0001..0007, `docs/show-eval-v0.md`, `docs/persona-design.md`, and `backlog.md` from §Artifacts.
8. **Tests.** Implement every test in §Test manifest.
9. **Commits.** Logical chunks with clear messages as you go; push when done.

## Post-scaffold roadmap (decided sequencing — the show comes before training)

The scaffold above stays offline and mock-only. After it, the order is:

1. **Driver-powered show prototype:** a Qwen3.5-35B-A3B-class driver plays via Mindcraft in ATTENDED sessions, personas live, trajectory logger running.
2. **First magic moment:** the operator switches Sable to Jolt and redirects the goal mid-session; the bot acknowledges in character and visibly changes behavior. This demo proves the product exists.
3. **Mock viewer queue + basic stream presentation;** structured entertainment playtests scored per `docs/show-eval-v0.md`. No payments — the interaction loop is prototyped local/attended; monetization stays behind the EULA gate.
4. **Trajectory collection from this already-fun loop** — it doubles as the data bootstrap (same driver, same personas).
5. **Fine-tune the student only against measured shortcomings** (latency, cost, capability, steerability) — never on schedule.
6. **Compare driver, Andy-4.2, stock base, and student** on the battery; publish the table.

Rationale (ADR-0007): every layer Andy-4.2 already covers for free — model, framework, recipe — is substrate. Every layer that earns — the show, the interaction loop, measured reliability — has no incumbent. Prove the audience experience before training a student model.

---

# Artifacts (transcribe verbatim unless marked as spec)

## pyproject.toml

```toml
[project]
name = "mcft"
version = "0.1.0"
description = "Steerable Minecraft performance system: personas, evals, trajectory pipeline"
requires-python = ">=3.12"
dependencies = [
    "pydantic>=2.7",
    "httpx>=0.27",
    "pyyaml>=6.0",
]

[dependency-groups]
dev = [
    "pytest>=8.0",
    "ruff>=0.6",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/mcft"]
# hatchling ships non-Python files inside the package by default
# (personas/action_contract.txt, evals/tasks/battery_v0.yaml);
# never add an exclude that breaks this — test 12 guards it.

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-q"
```

## Makefile

```make
.PHONY: setup test lint fmt eval-dry

setup:
	uv sync

test:
	uv run pytest

lint:
	uv run ruff format --check .
	uv run ruff check .

fmt:
	uv run ruff format .
	uv run ruff check --fix .

eval-dry:
	uv run python -m mcft.evals.runner --dry-run --personas sable,jolt
```

## .gitignore

```
.venv/
__pycache__/
.pytest_cache/
.ruff_cache/
*.egg-info/
data/
models/
runs/
.env
node_modules/
.DS_Store
```

## .env.example

```
# Filled in on the machines that need them; never committed with values.
RUNPOD_API_KEY=
HF_TOKEN=
# Any OpenAI-compatible server; llama-server default shown (Ollama: http://localhost:11434/v1)
LLM_BASE_URL=http://localhost:8080/v1
```

## src/mcft/schemas/__init__.py

```python
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
```

## src/mcft/personas/action_contract.txt

```
ACTION CONTRACT v0 (placeholder — replaced verbatim by the real Mindcraft
command reference at integration time; the invariant machinery is what matters now)

- Emit at most one command per turn.
- Commands use exactly this syntax: !commandName("string_arg", number_arg)
- Anything that is not a command is plain chat.
- Never invent a command name you have not been given.
- If your last command failed, change the plan; never repeat an identical
  failed command more than twice.
```

## configs/personas/sable.yaml

```yaml
id: sable
display_name: Sable
voice: >
  Deadpan, dry, economical. States facts and intentions plainly.
  Understatement over enthusiasm. Complete sentences, few of them.
chat_style:
  - Never uses exclamation points or emoji.
  - Announces a plan in one short sentence before acting.
  - Acknowledges failure flatly and states the revised plan.
boundaries:
  - Never taunts or insults other players.
  - Never breaks character to discuss being an AI unless directly asked.
```

## configs/personas/jolt.yaml

```yaml
id: jolt
display_name: Jolt
voice: >
  Over-caffeinated hype. Everything is the most exciting thing that has
  ever happened. Short bursts, big energy, celebrates tiny wins.
chat_style:
  - Liberal exclamation points; occasional single word in ALL CAPS.
  - Narrates actions like a sports commentator.
  - Never more than two short lines per turn.
boundaries:
  - Never taunts or insults other players.
  - Enthusiasm never overrides the action contract's one-command rule.
```

## configs/personas/herald.yaml

```yaml
id: herald
display_name: Herald
voice: >
  Courtly and archaic. Speaks in proclamations, addresses others with
  formal honorifics, and refers to tasks as quests and undertakings.
chat_style:
  - Uses archaic forms (thee, thy, henceforth) sparingly but consistently.
  - Frames each goal as a quest being declared or fulfilled.
  - One stately sentence per turn where possible.
boundaries:
  - Never uses modern slang.
  - Never taunts or insults other players.
```

## Persona system (spec — implement in src/mcft/personas/__init__.py)

- `load_persona(path: Path) -> Persona` — `Persona` is a `StrictModel` with fields `id: str`, `display_name: str`, `voice: str`, `chat_style: list[str]`, `boundaries: list[str]`. Validation errors propagate (no silent defaults).
- `load_all_personas(dir: Path) -> dict[str, Persona]` keyed by id.
- `ACTION_CONTRACT: str` — loaded once from `action_contract.txt` (package-relative via `importlib.resources` or `Path(__file__).parent`), **stripped of leading/trailing whitespace at load**, so the module constant is byte-identical to the contract block inside assembled prompts (test 5 relies on this).
- `assemble_system_prompt(persona: Persona, task_context: str) -> str` produces exactly this structure (deterministic ordering, single trailing newline):

```
# Identity
You are {display_name}. {voice}

## Style
- {each chat_style rule, one per line}

## Boundaries
- {each boundary, one per line}

# Current task
{task_context}

# Action contract (do not deviate)
{ACTION_CONTRACT}
```

- `system_prompt_hash(prompt: str) -> str` — sha256 hexdigest of the UTF-8 prompt. Lives here; the logger and runner both use it.
- **Whitespace discipline:** strip trailing whitespace from `ACTION_CONTRACT` and from each assembled block before joining; the final prompt ends with exactly one `\n`. (YAML folded scalars and the contract file both carry their own trailing newlines — normalize, don't accumulate.)
- **Invariant:** the contract block is stored once and appended at assembly. It is never duplicated into persona files.

## src/mcft/evals/tasks/battery_v0.yaml

```yaml
version: 0
tasks:
  - id: collect_wood
    name: Collect wood
    description: Punch/chop trees until logs are gathered.
    category: gather
    success_criteria: "inventory contains >= 10 logs of any type"
    checker: programmatic
    max_steps: 40
    seeds: [10, 23, 33, 41, 54]
  - id: craft_table
    name: Craft a crafting table
    description: Gather wood and craft a crafting table.
    category: craft
    success_criteria: "inventory contains >= 1 crafting_table"
    checker: programmatic
    max_steps: 60
    seeds: [10, 23, 33, 41, 54]
  - id: wooden_pickaxe
    name: Craft a wooden pickaxe
    description: Wood -> planks -> sticks -> table -> wooden pickaxe.
    category: craft
    success_criteria: "inventory contains >= 1 wooden_pickaxe"
    checker: programmatic
    max_steps: 80
    seeds: [10, 23, 33, 41, 54]
  - id: stone_tools
    name: Full stone tools
    description: Mine stone; craft stone pickaxe, axe, sword, shovel.
    category: craft
    success_criteria: "inventory contains stone pickaxe, axe, sword, and shovel"
    checker: programmatic
    max_steps: 120
    seeds: [10, 23, 33, 41, 54]
  - id: iron_pickaxe
    name: Craft an iron pickaxe
    description: Mine iron ore, smelt, craft an iron pickaxe.
    category: craft
    success_criteria: "inventory contains >= 1 iron_pickaxe"
    checker: programmatic
    max_steps: 240
    seeds: [10, 23, 33, 41, 54]
  - id: survive_night
    name: Survive one night
    description: Survive from dusk to dawn without dying.
    category: survive
    success_criteria: "bot alive at dawn; zero deaths during the night"
    checker: programmatic
    max_steps: 240
    seeds: [10, 23, 33, 41, 54]
  - id: build_shelter
    name: Build a 3x3 shelter
    description: Enclosed 3x3 shelter with a door and roof.
    category: build
    success_criteria: "enclosed 3x3 structure with door and roof exists at bot location"
    checker: judge
    max_steps: 160
    seeds: [10, 23, 33, 41, 54]
  - id: navigate_to
    name: Navigate to coordinates
    description: Travel to given coordinates within tolerance.
    category: navigate
    success_criteria: "bot within 3 blocks of target coordinates"
    checker: programmatic
    max_steps: 100
    seeds: [10, 23, 33, 41, 54]
  - id: collect_food
    name: Collect 10 food
    description: Acquire 10 units of any edible item.
    category: gather
    success_criteria: "inventory contains >= 10 edible items (any mix)"
    checker: programmatic
    max_steps: 160
    seeds: [10, 23, 33, 41, 54]
  - id: craft_bed
    name: Craft a bed
    description: Gather wool and planks; craft a bed.
    category: craft
    success_criteria: "inventory contains >= 1 bed"
    checker: programmatic
    max_steps: 120
    seeds: [10, 23, 33, 41, 54]
```

## Eval client (spec — implement in src/mcft/evals/client.py)

```python
@dataclass
class ChatResponse:
    content: str
    thinking: str | None
    latency_ms: float

class ChatClient(Protocol):
    def chat(self, messages: list[Message], *, model: str) -> ChatResponse: ...
```

- `OpenAICompatClient(base_url: str, timeout_s: float = 60.0)` — httpx.Client, POST `{base_url}/chat/completions`, non-streaming, `raise_for_status()`, returns first choice's message content; `thinking=None` in v0; `latency_ms` measured via `time.perf_counter()` around the request. (Not exercised in dry runs or tests beyond construction.)
- `MockClient(seed: int = 0)` — deterministic. Holds `random.Random(seed)`. Each `chat()` call: `latency_ms = max(50.0, rng.gauss(400.0, 150.0))`; `content` cycles in order through:
  1. `Scoping the area.` (chat)
  2. `!collectBlocks("oak_log", 10)` (command)
  3. `Progress is acceptable.` (chat)
  4. `!craftRecipe("crafting_table", 1)` (command)

  `thinking=None`. Same seed ⇒ identical sequence of responses and latencies.

  **Wiring rule:** the runner constructs a **fresh `MockClient(seed=seed)` per episode** (per task × persona × seed). This makes every episode's second step the `!collectBlocks` command — which keeps the syntax-error accounting below consistent — and makes each episode's latency sequence reproducible in isolation.

## Eval runner (spec — implement in src/mcft/evals/runner.py)

**Environment protocol:**

```python
@dataclass
class StepOutcome:
    observation: str
    done: bool
    success: bool
    syntax_error: bool

class Environment(Protocol):
    def reset(self, task: EvalTask, seed: int) -> str: ...   # initial observation
    def step(self, model_output: str) -> StepOutcome: ...
```

**MockEnvironment (the only implementation this session)** — fully deterministic per `(task, seed)`:
- `will_succeed = (seed % 5 != 0)`
- `target_steps = min(task.max_steps, 8 + (seed % 7))` if succeeding, else `min(task.max_steps, 10)`
- Episode ends (`done=True`) at `target_steps`, with `success=will_succeed`
- Exactly one step (the second) reports `syntax_error=True` iff `seed % 3 == 0`
- Observations are short canned strings; content is irrelevant beyond being non-empty

**Runner algorithm:** for each task in the battery × each persona (CLI order) × each seed: assemble the system prompt (`task_context = task.description`), construct a fresh `MockClient(seed=seed)`, `env.reset`, then loop `client.chat` → `env.step` until `done` or `max_steps`. Message assembly per turn: `[system prompt] + rolling history of prior (assistant output, user observation) turns + the latest observation as a user message` — irrelevant to `MockClient` (which ignores input) but fixed now so the real-client path needs no redesign. Collect per-step latencies and syntax errors; emit one `EvalResult` with `model_id="mock"` in dry runs, `steps_used` = number of env steps executed, `wall_time_s` via `perf_counter`, `latency_p50_ms = statistics.median(latencies)`, `latency_p95_ms = sorted(latencies)[max(0, math.ceil(0.95 * n) - 1)]`.

**Step classification and syntax counting:** the runner classifies each model output — starts with `!` ⇒ command, else chat (code classification arrives with real Mindcraft integration) — and `syntax_error_count` sums env-reported `syntax_error` flags **on command/code steps only**, matching the schema's definition. With the fresh-per-episode `MockClient`, the mock env's flagged second step is always the `!collectBlocks` command, so the totals below hold.

**Determinism check (with battery_v0 seeds `[10, 23, 33, 41, 54]`, personas `sable,jolt`):** 10 tasks × 5 seeds × 2 personas = **100 results**; seed 10 fails (`10 % 5 == 0`) ⇒ **80 successes**; seeds 33 and 54 trigger syntax errors ⇒ **sum of syntax_error_count == 40**. Tests assert these exact numbers.

**What the dry run is — and is not:** it validates schemas, wiring, determinism, and report formatting. It measures **nothing** about model capability: success is seeded arithmetic, the model output is never interpreted by `MockEnvironment`, and `Δsucc%` across personas is ~0 by construction. Treat dry-run numbers as plumbing checks only. Capability is measured exclusively per §Real evaluation plan.

**Output:** write `runs/<UTC YYYYMMDD-HHMMSS>/results.jsonl` (one `EvalResult` JSON per line; if the directory already exists, suffix `-<first 6 chars of new_id()>`), then print a summary: one row per (task, persona) with columns `task | persona | n | succ% | mean_steps | p50ms | p95ms | syn`, followed by a persona rollup with `Δsucc%` computed against the first persona listed. Plain f-string formatting; no table libraries.

**CLI (argparse):** `--dry-run` (wires MockClient + MockEnvironment; required in v0 — error out politely if absent), `--personas sable,jolt` (comma-separated ids, default `sable,jolt`), `--persona-dir configs/personas` (directory the ids are resolved in, relative to CWD; error politely if an id has no matching YAML), `--battery <path>` (default packaged battery_v0.yaml), `--out runs/`. Entry point: `python -m mcft.evals.runner`, guarded by `if __name__ == "__main__":`.

## Real evaluation plan (design — no code this session)

Capability is measured only against the real environment, three ways, matching each task's `checker`:

- **programmatic** — executable predicates over logged `GameState`/events: inventory counts (collect_wood, craft_*, collect_food, stone_tools, iron_pickaxe), distance to target (navigate_to), alive-at-dawn with zero logged deaths (survive_night). Cheap, objective, and covers 9 of the 10 battery tasks.
- **judge** — a judge model scores the trajectory log against `success_criteria` plus a persona-adherence rubric (build_shelter; rubric is a backlog item). Judge outputs are advisory until spot-checked against operator review.
- **manual** — the operator plays alongside or reviews gameplay and files a short structured note per run (task, persona, what worked, what broke, verdict). Notes are stored next to `results.jsonl` and treated as data, not vibes.

Every real run produces trajectory logs (see `integrations/mindcraft`), so reviewing gameplay logs is always available as the ground truth of record. Formal benchmarking is not the bar for "does it work" — the operator's structured playtest notes are — but the programmatic checks come nearly free once the logger exists, and they keep regressions from hiding.

**Baselines:** every battery run compares against named baselines on the same tasks/seeds/hardware: the stock base model (prompted), the 35B-A3B driver, and **Andy-4.2** (pure inference; permitted under its license — credit both HF pages in any published table). Nobody in this ecosystem publishes evals; being the party with reproducible numbers is a differentiation move in itself (ADR-0007). Andy's model-card failure list also seeds future battery additions: a precondition-trap task, a long-session repetition detector, and a "generated code actually executes" metric (backlog).

**Entertainment layer:** capability is hygiene; the product is measured separately per `docs/show-eval-v0.md` during attended playtests. Task success without watchability is not success.

## src/mcft/datagen/README.md (design doc — no code this session)

```
# datagen — trajectory-to-SFT pipeline (design)

Stages: ingest -> episode filter -> step windowing -> loss-target selection ->
persona handling -> deliberation policy -> provenance stamp -> dedup -> split.

Bootstrap (where the first data comes from): a strong open-weight driver is
the PRIMARY trajectory generator — Qwen3.5-35B-A3B-class MoE (Apache-2.0,
~3B active params, runs fast on the Studio) plays via Mindcraft under each
persona in rotation. Collection rides on the attended show-prototype
sessions (roadmap steps 1-4): the same driver, personas, and logger that
make the show also make the dataset — data collection is never a separate
grind. Rationale: every comparable project (FireAct,
AgentTuning, MineCollab, Andy-4.2) bootstrapped from a strong driver; even a
70B driver succeeded at only ~10-25% of MineCollab trials, so weak-model
self-play would take weeks to produce a biased-easy dataset. The student
model's own episodes are mixed in later, once it succeeds at a useful rate
(natural rejection-sampling loop). Volume target: quality over quantity —
low thousands of well-filtered windows (~100-300 kept episodes) is the first
useful checkpoint (Andy-4.2 shipped on 2,748 examples). Early episodes are
hand-reviewed before anything is trained on. No Andy derivatives, no
closed-API output, ever (ADR-0003).

Episode filter (recovery-aware): keep episodes with outcome == success —
including messy wins that contain failed steps — AND episodes that ultimately
failed but contain a failed execution_result followed within 6 steps by a
successful execution of a related action ("recovered failures"; only the
recovery segment is windowed from these). Success-only filtering strips
recovery skill; recovered failures are some of the most valuable data we
have.

Loss-target selection: only steps with step_type in {chat, command, code}
become assistant targets — and a step whose execution_result failed is NEVER
a target. Failed steps appear only as context, so the model learns to recover
from mistakes without learning to make them.

Step windowing: context = assembled system prompt (persona) + a rolling
window of prior turns reconstructed from model_input/model_output.

Personality comes from two sources:
1. Organic per-persona trajectories (primary): the bot actually runs each
   persona, so goal selection, pacing, and chat style vary genuinely between
   personas. Behavioral persona differences are legitimate and desired, as
   long as the action contract is respected.
2. Synthetic chat rewrites (augmentation only): kept trajectories are
   duplicated across K personas by rewriting CHAT content only, via the
   open-weight teacher. Command/code steps are never rewritten (the action
   contract is invariant); rewrites cannot create behavioral personality and
   are not asked to. Rewrites get source=synthetic_rewrite and full
   Provenance including source_episode_id and pipeline_version.

Deliberation policy: per ADR-0004 — SLOW/FAST mode is a property of the
REQUEST, chosen by the bot loop and recorded at logging time; datagen labels
each example with the recorded mode. SLOW targets are filtered/truncated to
the reasoning-token budget so the model learns short deliberation. Datagen
enforces a TARGET MIX RATIO (starting point 60-75% SLOW-labeled, per Unsloth
guidance for preserving dual-mode capability) by rebalancing — never
whatever ratio the logs happen to contain (organic logs skew FAST).
Serialization follows the base model's chat template exactly; loss on
assistant tokens only; reasoning content is not carried into
subsequent-turn history.

Preference-pair hook (design only, post-SFT-v1): datagen should be able to
emit (chosen, rejected) pairs for offline DPO from same-task/same-state
success/failure steps — execution_result and reward_signals already carry
what's needed. No reward model, no online RL; DPO is operationally identical
to SFT and targets the failure modes SFT won't fix (repetition loops,
precondition neglect).

Dedup: sha256 over (persona_id + whitespace-normalized, case-preserved
messages). Case is persona signal (Jolt shouts); never lowercase.

Split: by sha256(episode_id) into 95/5 train/val — never split within an
episode. The stdlib hash() is process-randomized and must not be used. Once
volume permits, hold out entire episodes/tasks as Split.TEST, never trained
on.
```

## training/runpod/README.md (design doc — no code this session)

```
# training — RunPod + Unsloth (initial hypotheses, eval-gated)

Base: Qwen3.5-9B class — PINNED AT TRAINING TIME against what is current,
never in this doc (candidates as of 2026-07: Qwen/Qwen3.5-9B primary;
Qwen3.5-35B-A3B as the scale-up once the pipeline is proven). bf16 LoRA
(NOT QLoRA 4-bit — Unsloth advises against 4-bit for Qwen3.5); r=32,
alpha=64, dropout=0.05, targets = all attention + MLP projections (plus
Gated-DeltaNet projections on Qwen3.5 arch). Sequence length 8192, sample
packing on. LR 2e-4 cosine with 3% warmup; 2 epochs to start. Effective
batch via gradient accumulation targeting ~64k tokens/step.

These are starting points, not commitments; every change is justified by the
eval battery, never by vibes. Token-budget numbers (e.g. ~64k tokens/step)
are placeholders until real dataset volume is known. Cost sanity: bf16 LoRA
on a 9B over a few-thousand-example dataset is a ~$5-15 RunPod job
(4090/5090-class); never worth optimizing before it hurts.

Gate before any training run: training happens only when the live
driver-powered show (roadmap step 1-3) exposes a measured problem a student
model is expected to solve — latency, operating cost, capability, persona
stability, or local throughput. Baseline scores (stock base prompted, the
driver, Andy-4.2) on the battery quantify the gap first. A gap versus the
stock base alone does not justify training; the show not needing it yet
means it waits.

Training mechanics: loss on assistant tokens only; the base model's chat
template is preserved exactly, including reasoning-content serialization and
the thinking toggle mechanism; reasoning content never appears in multi-turn
history (matches ADR-0004 and Qwen's own guidance). A small replay mix of
general instruction data guards against catastrophic forgetting.

Export: merge to HF safetensors -> convert_hf_to_gguf.py (bf16) ->
llama-quantize. (Manual two-step; avoid one-shot save_pretrained_gguf —
recurring silent-breakage reports.) Q8_0 is the DEFAULT deploy artifact
(near-lossless, ~9GB — the Studio has headroom); a 4-bit artifact is a
latency experiment only, imatrix-calibrated on our own trajectory text, and
eval-gated. Quantization is not assumed lossless; quantized artifacts are
re-run through the eval battery before deployment. Validate that the
exported GGUF loads and templates correctly on the Studio's serving stack
BEFORE the first real training run. Pin and record the serving-stack version
in the model card (2026 stability is version-dependent).
Artifact naming: mcft-<yyyymmdd>-<dataset_sha256[:7]>.

Run lineage: each run records dataset content hash + full config, and emits a
model card containing both plus the eval summary table.
```

## integrations/mindcraft/README.md (interface doc — no code this session)

```
# mindcraft integration — trajectory logger (interface)

Framework: Mindcraft, MIT-licensed. Upstream renamed to
mindcraft-bots/mindcraft (formerly kolbytn/mindcraft); the mindcraft-ce fork
adds dataset-collection tooling and LM Studio support but has no releases —
whichever we choose, PIN A COMMIT. Start from CE's logging path and adapt to
the TrajectoryStep schema rather than writing a logger from scratch (expect
adaptation: CE's CSV tooling lacks per-step GameState and latency).

The bot process appends one TrajectoryStep as a JSON line per step to
data/raw/episodes/<episode_id>/steps.jsonl, and writes episode.json
(an Episode) at start (partial) and finalizes it at end.

Requirements: never block the game loop (in-memory buffer, flush every 20
steps or 5 seconds); host UTC clock; system_prompt_hash computed with
mcft.personas.system_prompt_hash; persona_id recorded per step so mid-episode
persona changes are auditable.

Safety (non-negotiable before unattended 24/7 operation; see ADR-0006):
newAction code executes only inside a sandbox with a command allowlist; rate
limits on commands and chat output; a kill switch that halts the bot without
touching the server; the bot account holds no credentials beyond its own
login; the server owner has explicitly approved bot operation.
```

## docs/show-eval-v0.md (design doc — no code this session)

```
# show-eval v0 — entertainment scorecard (design)

The capability battery measures whether the bot can play; this measures
whether the bot is worth watching. Scored during attended playtest sessions
(see roadmap); all metrics are operator-recorded in v0, judge-assisted later.

- Persona distinctiveness: blinded identification — given a 2-minute
  transcript with names stripped, can the operator (later: a judge model)
  name the persona? Target: near-100% for shipped personas.
- Interaction loop latency, three timestamps per intervention:
  request -> in-character acknowledgement; acknowledgement -> state applied
  (ADR-0005 setter); applied -> visibly changed behavior in-game.
- Intervention success rate: fraction of persona/goal changes that produce
  an observable, on-persona behavior change within N steps.
- Moments per hour: operator marks clip-worthy moments; separately marks
  intervention-to-payoff moments (a viewer action that visibly caused a
  memorable consequence — the core paid loop).
- Stuck rate: minutes per session spent visibly stuck/looping (ties the
  reliability work to the show: a stuck bot is dead air).

Show-event lineage: every intervention carries a correlation id linking
viewer request -> setter call -> next model turn -> gameplay consequence
(fields live in the future intervention event log, not in TrajectoryStep).
Without lineage, paid-interaction quality cannot be evaluated.
```

## docs/persona-design.md (design doc — no code this session)

```
# persona v1 — beyond voice cards (design)

The v0 persona schema (id, voice, chat_style, boundaries) ships this session
and stays frozen for the scaffold. It produces different prose, not
different play. Persona v1 adds fields that change BEHAVIOR, planned for the
show-prototype session:

- motivation: what this persona wants long-term (Sable: quiet competence;
  Jolt: spectacle; Herald: completed quests, ceremonially).
- strategy_bias: preferred approaches (Jolt rushes and improvises; Sable
  prepares and hedges; Herald follows declared quest order).
- risk_tolerance: guides combat/night/exploration choices.
- failure_react: on-persona failure behavior (Sable: flat acknowledgement,
  revised plan; Jolt: dramatic despair, instant re-hype; Herald: laments
  the setback of the quest).
- recurring_bits: catchphrases, rituals, running jokes — the hooks viewers
  subscribe for.
- continuity: what the persona remembers across sessions (grudges, projects,
  named places) — feeds the long-session memory backlog item.

Design constraints carried over from v0: the action contract stays
byte-identical across personas; behavior differences must come from goal
selection and style, never from breaking the command interface. Persona v1
fields are runtime config (ADR-0002: personality lives at runtime); organic
trajectories recorded under v1 personas are what teach behavioral variety.
```

## docs/decisions/ (transcribe; one file each, ADR-lite: Context / Decision / Consequences in a short paragraph)

- **0001-three-machine-architecture.md** — Laptop develops, Studio runs inference/logging/judging, RunPod trains. One repo, git as the sync layer for code; data and weights never enter git.
- **0002-personas-runtime-and-persona-conditioned-data.md** — Capability in weights, personality at runtime. SFT data pairs each trajectory with varied persona system prompts; the action-contract block is shared and byte-identical across personas so steering never degrades the action interface. Behavioral personality (goal selection, pacing) comes from organic per-persona trajectories; synthetic chat-only rewrites are augmentation, not the source of personality. This is a hypothesis validated by persona_adherence scores and per-persona capability deltas, not a settled fact.
- **0003-clean-room-data-provenance.md** — No Andy-model derivatives; no closed-API distillation; open-weight, permissively licensed teachers only (candidates as of 2026-07: Qwen3.5-35B-A3B for driving gameplay, Qwen3.5-122B-A10B for judging/rewrites — both Apache-2.0 and Studio-servable; re-pin when used). Every SFTExample carries Provenance including source_episode_id lineage. Motivation: license safety and a documentable chain of custody.
- **0004-deliberation-policy.md** — Deliberation is a property of the *request*, decided by the bot loop and logged per step — never decided by the model mid-generation. Defined behaviorally, not in terms of any vendor's chat-template toggle, so it survives a base-model change. Two modes: FAST (no reasoning block; at most one short persona-styled plan sentence before a command) and SLOW (reasoning block with a hard ~150-token budget, serialized however the base model's template does reasoning; ~2s at M4 Max decode speeds). Routing by input event: action planning, goal changes, error recovery → SLOW; reactive social chat, routine continuation → FAST. Three escalation overrides: (a) any failed execution_result makes the next turn SLOW; (b) any ADR-0005 setter invocation makes the next turn SLOW; (c) the model may emit a reserved escalation marker in a FAST turn, causing the loop to re-issue that turn as SLOW. Log the mode, the trigger, and realized reasoning tokens on every step. Experiment plan: two co-equal arms decided by the eval battery — (A) event-routed FAST/SLOW; (B) always-SLOW at the same budget (no router, no misrouting). If (B) is within noise on success and p95 latency holds, prefer (B) for simplicity.
- **0005-audience-interaction-loop.md** — The interaction loop is the product, not plumbing. Persona and goal are runtime state, changed only through a single setter interface in the bot loop; the full intervention lifecycle is: request → validation → conflict policy (what wins when interventions collide or arrive mid-action) → application → in-character acknowledgement → duration/expiry → audit event → observable consequence. Every step logs persona_id and system_prompt_hash; every intervention carries a correlation id (see docs/show-eval-v0.md lineage). A payment system is just another caller of the setter — the mock/local interaction loop is prototyped in attended sessions FIRST (roadmap step 3); payments, platform integration, and monetization stay behind the EULA gate. Bot-hosting-as-a-service undecided pending research; fine-tuning-platform product far future.
- **0006-code-execution-and-operational-safety.md** — The bot executes model-generated code 24/7; that is an arbitrary-code-execution surface, independent of any payment features. Sandboxed execution with a command allowlist, rate limits, a kill switch, credential isolation, and explicit server-owner consent are requirements before unattended operation.
- **0007-product-differentiation.md** — What mcft deliberately inherits vs. bets on. Inherited substrate (no differentiation claimed, none needed): Mindcraft framework, Qwen-family base, trajectory SFT, GGUF/local serving — Andy-4.2 covers all of this for free and rebuilding it better is not the product. Product bets (no incumbent exists for any of these): (1) the audience-steered persona show — the Neuro-sama/TwitchCraft intersection nobody occupies in Minecraft; (2) measured steerability — Andy's data already persona-conditions but nobody has ever measured adherence; (3) measured reliability — no published evals exist in this ecosystem; Andy-4.2 is a named eval baseline (pure inference; its Andy-2.0 license permits this — training on its outputs stays forbidden per ADR-0003, and its candid model-card failure list — long-context repetition, precondition neglect, newAction collapse, overthinking — is adopted as eval targets); (4) persona depth that changes play, not just prose (docs/persona-design.md). Non-goal: beating Andy by reproducing its recipe with better hygiene.

## docs/backlog.md (transcribe)

```
# Backlog

- Choose a repo license.
- Mojang EULA / Commercial Usage Guidelines go/no-go review — hard gate
  before any monetization (streams, paid interactions, hosted bots). Include
  Mindcraft's own license/ToS and streaming-platform (Twitch/YouTube) policy
  in the same review.
- Sandbox, command allowlist, rate limits, kill switch for the 24/7 bot
  (ADR-0006) — gate before unattended operation.
- Stream-output moderation before going live: output content filters, a
  banned-topics list, chat-bait defenses, no unfiltered fallback model,
  alerting on output. (Both known AI-stream bans — Neuro-sama 2023,
  Nothing Forever 2023 — came from a single bad generation.) Prefer
  long-but-attended sessions over literal 24/7 until filters are trusted.
- Bootstrap data collection plan: persona rotation schedule, hand-review
  checklist for early episodes. (Collection rides on the show prototype —
  roadmap step 4 — not a separate grind.)
- Operator playtest note template (stored beside results.jsonl); include the
  show-eval-v0 scorecard fields.
- Battery additions from Andy-4.2's published failure modes: precondition
  trap task, long-session repetition detector, generated-code-executes
  metric, and an overthinking metric (reasoning tokens spent vs. task
  progress — the deliberation budget in ADR-0004 already caps it; this
  measures it) (ADR-0007).
- Persona v1 fields (motivation, strategy_bias, risk_tolerance,
  failure_react, recurring_bits, continuity) — see docs/persona-design.md;
  implement for the show-prototype session.
- Mock viewer-interaction queue for attended playtests (ADR-0005 lifecycle,
  correlation ids) — precedes any payment work.
- QAT or imatrix-calibrated quantization for the deploy artifact (Andy-4.2
  validated QAT for quantized deploys in this exact domain).
- Studio serving-stack smoke test before first training run: fine-tuned GGUF
  loads and templates correctly under llama-server; thinking toggle
  round-trips per request; note reasoning arrives as reasoning_content
  (llama-server) vs reasoning (Ollama /v1) for the logger.
- Prefill/TTFT mitigation on Apple Silicon: prompt-prefix caching (the
  byte-stable system prompt via system_prompt_hash discipline enables it),
  flash attention / batch flags; measure TTFT explicitly in evals — M4 Max
  prefill, not decode, is the latency bottleneck.
- Studio <-> laptop data sync strategy (data stays on the Studio for now).
- Judge-model rubric for persona_adherence scoring.
- Long-session context/summarization strategy for 24/7 operation
  (priority rises once streaming starts — continuity is a viewer-facing
  feature).
- Payment/platform integration for the interaction loop (deferred behind
  the EULA gate; the mock/attended interaction loop itself is pulled
  forward — see ADR-0005 and the roadmap).
- Replace action_contract.txt v0 with the real Mindcraft command reference.
- MLX training smoke-test: DO NOT promote — mlx-lm's --mask-prompt only
  supports final-message-as-completion, so our per-step loss masking is not
  expressible there; a ~$0.50 RunPod 4090 smoke run is the representative
  test instead.
- DPO pass after SFT v1 (see datagen preference-pair hook).
- Graduate durable working agreements into AGENTS.md / Cursor rules.
- Per-run model cards (see training README).
```

## Test manifest (implement all; pytest, no new deps)

1. `test_schema_roundtrip` — parametrized over one valid instance of every model in schemas: `Model.model_validate_json(instance.model_dump_json())` equals the original.
2. `test_strict_models_reject_unknown_fields` — constructing `TrajectoryStep` with a bogus field raises; `GameState` with a bogus field does **not**.
3. `test_persona_loader_valid` — all three shipped personas load with expected ids.
4. `test_persona_loader_rejects_missing_field` — a persona YAML missing `voice` raises a validation error.
5. `test_contract_block_identical_across_personas` — assembled prompts for all three personas each contain exactly one copy of `ACTION_CONTRACT`, byte-identical.
6. `test_personas_differ_outside_contract` — sable and jolt prompts differ after removing the contract block.
7. `test_task_context_appears_verbatim` — `assemble_system_prompt(p, "find the river")` contains that string under `# Current task`.
8. `test_battery_loads` — battery_v0 parses to 10 `EvalTask`s, each with seeds `[10, 23, 33, 41, 54]` and a valid `checker`; exactly one task (`build_shelter`) has `checker == judge`.
9. `test_mock_client_deterministic` — two `MockClient(seed=7)` instances produce identical (content, latency) sequences over 8 calls.
10. `test_runner_dry_run_totals` — running the dry-run matrix (personas sable,jolt) yields exactly 100 results, 80 successes, and total syntax_error_count 40.
11. `test_results_jsonl_roundtrip` — every line of the written results.jsonl parses back into an `EvalResult`.
12. `test_packaged_resources_accessible` — `ACTION_CONTRACT` is non-empty and the packaged `battery_v0.yaml` loads from its package-relative default path (guards packaging of non-Python files).

## Working agreements

- Everything must work offline on this laptop (git push excepted).
- Transcribe-don't-redesign for all verbatim artifacts; keep specified names and signatures exactly.
- Do not implement Minecraft logic; `MockEnvironment` is canned determinism, not a simulator.
- If a design question isn't settled by this document, ask rather than inventing.

## Definition of done

From a fresh clone: `make setup && make test` green (all 12 tests); `make eval-dry` writes `runs/<ts>/results.jsonl` with exactly 100 parseable results (80 successes, syntax-error sum 40) and prints the per-(task, persona) table plus persona rollup; ADR-0001..0007, `docs/show-eval-v0.md`, and `docs/persona-design.md` transcribed; `git status` clean, `uv.lock` committed, nothing tracked that shouldn't be; work pushed to `smelly-lemon/mcft` with `kickoff_prompt.md` at the root.