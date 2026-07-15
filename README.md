# mcft — Steerable Minecraft Performance System

A runtime-steerable Minecraft performance system: an AI bot with distinct,
audience-steerable personas, streamed live — with a fine-tuning pipeline as
its engine. The show is the product; the model is infrastructure.

**Source of truth:** [`kickoff_prompt.md`](kickoff_prompt.md). Re-read it at
the start of any session that references it.

## Quickstart

```sh
make setup && make test && make eval-dry
```

`eval-dry` runs the deterministic mock eval matrix (plumbing validation
only — it measures nothing about model capability) and writes
`runs/<timestamp>/results.jsonl`.

## Three execution contexts

- **Laptop:** development, tests, dry-run evals (offline, mock-only).
- **Mac Studio (M4 Max, 128GB):** production — local inference via llama.cpp
  `llama-server` (Ollama/LM Studio as fallbacks), the Mindcraft bot,
  trajectory logging, judge-model scoring.
- **RunPod (rented CUDA):** training only — Unsloth LoRA (bf16) → GGUF
  export → back onto the Studio.

## Core principles

1. **Capability lives in weights; personality lives at runtime.** Personas
   are config files; runtime state changes only through the audience
   interaction loop (ADR-0005).
2. **The trajectory schema is the keystone.** The logger writes it, datagen
   filters it, SFT formatting consumes it, evals score against it.
3. **Clean-room data provenance.** No Andy-model derivatives, no closed-API
   distillation; every dataset row carries source metadata.
4. **Interface-driven model access.** All model calls go through an
   OpenAI-compatible abstraction; core code never imports provider SDKs.

## Layout

- `src/mcft/schemas/` — all pydantic models (single source of truth)
- `src/mcft/personas/` — persona loader + system-prompt assembly
- `src/mcft/evals/` — eval client, runner, task battery
- `src/mcft/datagen/` — trajectory-to-SFT pipeline (design doc)
- `configs/personas/` — shipped personas (sable, jolt, herald)
- `integrations/mindcraft/` — trajectory logger interface (design doc)
- `training/runpod/` — training recipe (design doc)
- `docs/decisions/` — ADR-0001..0007
- `docs/show-eval-v0.md` — entertainment scorecard (design)
- `docs/persona-design.md` — persona v1 spec (design)
