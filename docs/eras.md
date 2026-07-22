# Data eras

Scaffold changes create eras; cross-era metrics are not comparable. Era
boundaries below are UTC. Analysis code (analysis/teacher_readiness.py) keys
off these boundaries.

| era | start | end | scaffold | world | notes |
|---|---|---|---|---|---|
| A_dev | 2026-07-16 ~23:00 | 2026-07-17 16:20 | pre-patch dev | world (seed unknown) | single/dual bot bring-up, spawn-protection bug |
| B_patched | 2026-07-17 16:20 | 2026-07-19 02:00 | placeHere retry, givePlayer window, did-you-mean, loop-breaker v1 | world | first cooperation |
| X_outage | 2026-07-19 02:00 | 2026-07-19 15:15 | (excluded) | world | Ollama runner wedge; journals clobbered pre-memguard |
| C_churn | 2026-07-19 15:15 | 2026-07-19 21:55 | loop-breaker v2, collect guard, memguard, goto near-arrival, keep_alive -1 | world | watchdog v3/v4 churn window |
| D_clean | 2026-07-19 21:55 | 2026-07-20 20:52 | + taskguard, watchdog v4, 2-agent check | world | best pre-reset era; E1-E6 deployed 18:03 UTC 07-20 for the 2.5h smoke soak |
| E_baseline | 2026-07-20 20:53 | 2026-07-21 17:20 | D scaffold + E1-E6 + siteguard v2 | worldE, seed 4770568866102418726, site (0, 86, 64) | clean baseline; called at T+20.4h (rates flat, marginal hours redundant) |
| F_intent | 2026-07-21 17:27 | 2026-07-21 20:37 | E scaffold + intent graph v1 ON + chestguard | worldE (continuous) | DEADLOCKED - see below; data unusable for the ablation |
| F2_intent | 2026-07-21 20:42 | 2026-07-22 03:24 | F scaffold + intent graph v1.1 (self-healing) | worldE (continuous) | blocks decay 20min, system goals unkillable, switch revives, auto-heal; ablation-validated |
| **F3_intent** | **2026-07-22 03:24** | (open) | F2 + intent v1.2 anti-ping-pong + chestguard v2 (auto-clear) | worldE (continuous) | overnight run; block steering excludes goals left <20min ago; chest covers cleared automatically |

Era-F post-mortem (the soak did its job): loop-breaker `block` ops from two
bots sharing one graph permanently blocked every node inside ~2h, including
the mission root. With everything blocked, `goalSwitch` refused all targets
and `goalAdd` defaulted its parent to the (empty) active pointer ("parent
'undefined' not found") - a deadlock with no model-reachable exit. Bots ran
headless (empty INTENT) for the remainder. Infra itself was clean: zero JS
errors, chestguard verified live. Positive signal: models used the op
surface correctly (clean goalAdd with a real why, goalSwitch after walls).

Era-F2 fix (v1.1, both runtimes + 21-check smoke + 19 pytest): blocks carry
a 20-minute decay timer; system mission goals never change status on block
(pointer steers away instead); goalSwitch accepts exact titles and revives
blocked goals; goalAdd falls back to the mission root; an all-blocked tree
auto-heals; pointerless bots are auto-pointed at the next open leaf on view
render. Live graph reseeded pristine at F2 start.

## Ablation run-20260721-1614 (E vs F2, paired)

3 pairs x 35 min, alternating E,F from identical era-E-end snapshots
(world + journals), qwen3.6:35b both arms, eval server, live show paused
23:14-02:47 UTC. Data: `analysis/runs/run-20260721-1614/` (laptop) +
`tim4:~/Desktop/mindcraft/ablation/`. Orchestrator: 6/6 clean handoffs.

Results (arm E / arm F2): steps 254/277, fail rate 9.8%/7.2%, exact
repeats 75/65 per 1k, alternations 75/130 per 1k, chest share 1.0/1.0,
journal GOAL drift 0/0, lat p50 13.6s/14.7s p95 41.6s/33.7s. Intent: path
on 100% of F steps, 2 deliberate goalSwitch ops, no deadlock.

Read: F2 wins on failures and exact repeats, loses on alternations - the
block op ping-pongs pointers between two sibling goals (walls<->roof) and
the model alternates outputs with it. Neither arm drifted journals (E's
E1-E6 prompt discipline already handles it; F makes it structural). Net:
graph is mechanically sound and pays its way on teacher-data annotation
(intent_path per step); needs v1.2 anti-ping-pong (don't steer back to
the goal just left within the cooldown) before it clearly wins on meters.

Era-E note: at 21:19 UTC the stack restarted onto code that includes the
DORMANT intent-graph integration (settings.mcft_intent=false). Verified
byte-identical prompts (docs gate check) and identical behavior; the only
delta is a new `intent_path: null` field in steps.jsonl.

Era-E final (3,720 steps, 2 bots, 20.4h): goToCoordinates 0.3% fail,
placeHere 1.0%, craftRecipe 4.8% (era D: 30%+), givePlayer 46% but only 28
uses (chest-first prompting worked - 652 chest ops). Dominant defect:
bots buried their own chest under a block -> openContainer threw ->
takeFromChest 21%/putInChest 15%/viewChest 24% fails, 124/130 sharing that
signature; exact-repeat 69/1k driven by chest retries. Fix = chestguard
(ops/patch_chest_open.py) at the era-F boundary: pre-checks the covering
block and names it, catches open failures with actionable text.

Era-E archives: world-eraE-end-2026-07-21.tgz (17M, consistent save-off
snapshot - the era-F/E ablation launches paired episodes from it),
corpus-eraE-final-2026-07-21.tgz (9.5M).

Era-F activation verified: intent_path populated per step, INTENT section
in deployed profiles, mindserver serving views (single writer).

Era-F3 (v1.2, overnight 07-22): two ablation-driven fixes. (1) Anti-ping-
pong: the graph remembers per-bot "recently stepped away" goals (20-min
TTL, persisted in `recent_steps_away`); block steering excludes them from
sibling choice and leaf search, falling back to any open leaf only when
everything is avoided. A deliberate goalSwitch clears the guard for that
goal. (2) Chestguard v2: both ablation arms kept failing on the dirt-
covered chest baked into the era-E snapshot - the guard now auto-clears
soft covers (dirt/sand/planks/...) via breakBlockAt before reporting.
Validated: 24-check JS smoke on Studio, 22 pytest, JS-mutated graph
round-trips through the Python schema. Fork commit a77c555; F2 pointer
state (sable:roof, jolt:farm) carried across the restart.

Archives: era-D world in `tim4:~/Backups/mcft/world-eraD-2026-07-20.tgz` (54M,
includes nether/end); corpus snapshots nightly in `tim4:~/Backups/mcft/` and
pulled to `~/mcft-backups/` on the laptop every 6h.
