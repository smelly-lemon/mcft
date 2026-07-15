# ADR-0003: Clean-room data provenance

**Context.** Community datasets in this space (Andy) have unverifiable,
mixed provenance; closed-API terms restrict training competing models; a
monetized product needs a documentable chain of custody.

**Decision.** No Andy-model derivatives, no closed-API distillation.
Open-weight, permissively licensed teachers only (candidates as of 2026-07:
Qwen3.5-35B-A3B for driving gameplay, Qwen3.5-122B-A10B for judging/rewrites
— both Apache-2.0 and Studio-servable; re-pin when used). Every SFTExample
carries Provenance including source_episode_id lineage.

**Consequences.** License safety and a documentable chain of custody. Andy
models may still be run for pure-inference eval baselining (ADR-0007) —
their outputs just never enter training data.
