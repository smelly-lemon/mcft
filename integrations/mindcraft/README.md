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
