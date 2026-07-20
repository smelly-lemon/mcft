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
| **E_baseline** | **2026-07-20 20:53** | (open) | D scaffold + E1-E6 + siteguard v2 | **worldE, seed 4770568866102418726, site (0, 86, 64)** | clean baseline for the master plan; fork commit "Era E reset" |

Era-E note: at 21:19 UTC the stack restarted onto code that includes the
DORMANT intent-graph integration (settings.mcft_intent=false). Verified
byte-identical prompts (docs gate check) and identical behavior; the only
delta is a new `intent_path: null` field in steps.jsonl. Era-F activation =
scp mcft_intent.json + profiles regenerated with --intent + toggle true.

Archives: era-D world in `tim4:~/Backups/mcft/world-eraD-2026-07-20.tgz` (54M,
includes nether/end); corpus snapshots nightly in `tim4:~/Backups/mcft/` and
pulled to `~/mcft-backups/` on the laptop every 6h.
