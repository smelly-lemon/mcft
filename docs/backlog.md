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
