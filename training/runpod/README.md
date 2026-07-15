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
