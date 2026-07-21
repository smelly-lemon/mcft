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
| **F_intent** | **2026-07-21 17:27** | (open) | E scaffold + intent graph ON + chestguard | worldE (continuous) | era-F candidate: INTENT prompts, !goal ops, graph journals, loop-breaker v3 |

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

Archives: era-D world in `tim4:~/Backups/mcft/world-eraD-2026-07-20.tgz` (54M,
includes nether/end); corpus snapshots nightly in `tim4:~/Backups/mcft/` and
pulled to `~/mcft-backups/` on the laptop every 6h.
