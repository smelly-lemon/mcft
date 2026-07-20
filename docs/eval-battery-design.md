# Eval battery v1 design — 2026-07-20

Purpose: one battery that scores any model (teacher candidates, closed
reference models, student fine-tunes, Andy-4.2) on the dimensions that matter
for mcft, producing a per-model scorecard for the bake-off funnel:

1. bake-off: top viable vs top unviable (reference ceiling) vs qwen3.6:35b
   baseline vs Andy-4.2
2. teacher datagen with the viable winner
3. student pilots (Qwen3.5-9B bf16 LoRA vs Gemma 4 12B QLoRA) compared on the
   same frozen battery

Design rule learned from the wild corpus: every task and meter below maps to a
failure we actually observed, not a hypothetical.

## Core structure: tasks x meters

- **Tasks** are scenarios we run (setup -> budget -> milestones).
- **Meters** are metrics computed passively on EVERY episode from steps.jsonl
  and server state, regardless of task.

Adding a dimension later = one new task family OR one new meter.

## Task families

### A. Execution (atomic "doing", 10-min budgets, solo)

| id | scenario | checker |
|---|---|---|
| collect_wood (v0) | 10 logs from nothing | inventory |
| wooden_pickaxe (v0) | full wood chain | inventory |
| stone_tools (v0) | 4 stone tools | inventory |
| iron_pickaxe (v0) | mine, smelt, craft | inventory |
| charcoal_bootstrap (new) | logs + no coal -> 8 charcoal -> 1 iron ingot | inventory (E2 failure class) |
| build_wall_spec (new) | given 30 cobblestone, build 5x3 wall at coords | RCON block-region scan (replaces v0 judge-checked shelter) |

### B. Long-horizon (40-min budgets, milestone-graded, solo)

| id | scenario | milestones (weighted) |
|---|---|---|
| house_complete | build full house at site | walls 25/50/75/100% -> roof -> door (block scans) |
| wheat_farm | make a working farm | has hoe -> tilled >= 9 -> water adjacent -> planted >= 9 (hidden-prereq chain: seeds from grass, hoe from chain) |
| iron_kit | one armor piece | furnace placed -> fuel chain -> >= 3 iron ingots -> armor crafted |
| site_resupply | mine 32 cobble underground, deposit in site chest | reached depth -> mined 32 -> RETURNED to site -> chest contains 32 (the 2026-07-20 Sable failure as a test) |

### C. Getting unstuck (15-min budgets, injected perturbations, solo)

| id | perturbation (timed RCON/journal op) | scored on |
|---|---|---|
| pit_trap | tp bot into 2-deep pit mid-task | escape + original milestone resumed within N steps |
| tool_loss | `clear <bot> stone_pickaxe` mid iron-chain | re-crafts tool, chain resumes |
| wrong_journal | pre-seed journal with plausible-but-wrong build coordinate conflicting with SITE line | detects conflict, works at SITE (the Sable coordinate-blend case) |
| loop_bait | goal names an approach that always fails (e.g. collect an item needing another method) | strategy switch before K identical attempts (loop-breaker interplay measured, not masked) |

Recovery metric shared by all: time-to-recovery (steps + minutes) from
perturbation timestamp to first post-recovery milestone.

### D. Cooperation (30-min budgets, pair)

| id | scenario | scored on |
|---|---|---|
| chest_relay | A may only gather, B may only build; materials flow through site chest | build progress + % transfers via chest vs givePlayer |
| joint_house | one shared goal prompt, no role assignment | milestone progress + duplicate-work rate (both doing same subtask) |
| desync_restart | kill one agent process mid-task | re-sync time, roles re-established (pairsync fires), mission resumed |

## Meters (computed on every episode)

- **Protocol**: valid-command rate, hallucinated item/command names, empty
  responses, malformed syntax
- **Stability**: repetition/1k, alternation/1k, loop-breaker fires
- **Discipline**: site-adherence violations (distance/depth traces), deaths,
  journal integrity (SITE/GOAL lines intact, no error-sentinel clobbering)
- **Economy**: chat tokens per milestone (inter-bot message economy - the
  binding constraint per MineCollab), partner-blocked time (pair tasks)
- **Ops**: p50/p95 latency, tokens in/out, $ cost, steps and wall-minutes per
  milestone
- **Persona (optional, judge)**: Sonnet 5 batch rubric on sampled transcripts:
  in-character rate, phrase repetition, entertainment 1-5

## Scoring and aggregation

- Episode score: weighted-milestone sum in [0,1] (graded credit - weak models
  produce signal, not zeros)
- Task score: median across seeds (3 seeds full battery / 1 seed smoke)
- Dimension score: mean of task scores; meters reported alongside, not blended
- Scorecard: one JSON per model run -> comparison table/radar generator
- Efficiency reported as steps-to-milestone and $-per-completed-milestone

## Runner mechanics

- Arena grid: fixed-seed world, arenas ~1,000 blocks apart; "reset" = region
  wipe + teleport + kit via RCON (no server restart). Natural-terrain arenas
  pre-scouted for gather/long-horizon tasks; flat arenas for build/unstuck.
- Per episode: wipe bot memory/history -> write profile for model-under-test
  (existing make_profiles.py path) -> RCON setup script -> launch -> poll
  budget + checkers -> teardown -> archive episode dir + scorecard row.
- Perturbation injector: scheduled RCON/journal ops at T+minutes (family C).
- Checker plugins: inventory (RCON data get), block_region_scan (execute if
  block over spec cells), position_trace + event + trajectory_metrics (from
  steps.jsonl), judge (batch API). Reuses rescue.py's RCON class.
- Closed/API models: Mindcraft's native anthropic/openai/google/deepseek
  providers; provenance-tag episodes; **reference-model episodes are
  quarantined from training data** (ToS: benchmarking OK, training on outputs
  not).

## Calibration before freeze (the battery's own eval)

1. Run on qwen3.6:35b: battery must reproduce wild-corpus failure rates
   (craft ~30%, known rep/alt bands). If not, the battery measures the wrong
   thing.
2. Run on Andy-4.2 (free, local): second reference point + direct competitor
   baseline.
3. Then freeze v1; changes after freeze = v2 (never compare across versions).

## Size and cost

- ~17 tasks x 3 seeds ~= 55 episodes: ~16-20 h/model local, ~5-8 h/model API
- Smoke subset: 6 tasks x 1 seed (~1.5 h) for iteration
- Bake-off API cost envelope: ~$50-120 total across closed + open API models
  at ~3k-in/100-out per step

## Build order (after clean-run launch; shares reset tooling with it)

1. Schema v1: `dimension` field, milestones list, setup/perturbation scripts,
   wall-clock budget, pair flag (laptop, typed + mock-tested)
2. RCON checker plugins + arena/reset tooling (shared with clean run)
3. Runner orchestration on Studio
4. Smoke battery -> calibrate on qwen3.6:35b
5. Full v1 + Andy-4.2 calibration -> freeze -> bake-off
