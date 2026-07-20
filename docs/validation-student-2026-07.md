# Student-Model Claim Validation Report — July 20, 2026

Independent verification of the research doc's claims about candidate student
models for the Minecraft fine-tune (subagent-run, primary sources: HF model
cards, license texts, Google/Qwen/Unsloth docs, llama.cpp/Ollama PRs).

---

## Claim-by-claim verification

### 1. Qwen3.5-9B / Andy-4.2 / Gated DeltaNet — VERDICT: Confirmed

Qwen3.5-9B exists (released March 2, 2026, alongside 0.8B/2B/4B), is Apache 2.0
(HF card license field), multimodal, 262k native context. Hybrid architecture
confirmed: 8 x (3 x Gated DeltaNet -> FFN -> 1 x Gated Attention -> FFN), plus
MTP heads. Andy-4.2 lists `base_model: Qwen/Qwen3.5-9B` in HF metadata. The
"beats Gemma 4 12B on 5 of 8 benchmarks" is a real community claim, but other
benchmark cuts score it 2-2 or 4-6 — Qwen wins knowledge/science/agentic TAU2,
Gemma wins coding/multilingual.

- https://huggingface.co/Qwen/Qwen3.5-9B
- https://github.com/QwenLM/Qwen3.5
- https://huggingface.co/Mindcraft-CE/Andy-4.2
- https://gemma4all.com/blog/gemma-4-vs-qwen-3-5-benchmarks

### 2. Qwen3.6 small tier — VERDICT: Corrected (does not exist)

There is NO small Qwen3.6 tier as of July 20, 2026. Qwen3.6 is exactly two open
models: Qwen3.6-35B-A3B (MoE, April 16) and Qwen3.6-27B (dense, April 22), both
Apache 2.0, agentic-coding-focused, with MTP heads. The claim conflated it with
Qwen3.5, whose small tier (0.8B/2B/4B/9B) shipped March 2 with the "Towards
Native Multimodal Agents" framing. Support: llama.cpp supports both families
(full support ~build b7990); Ollama has official qwen3.5 + qwen3.6 entries;
Unsloth supports Qwen3.6 fine-tuning (PR #5257). Ollama currently fails to load
community MTP GGUFs for Qwen (issue #16282).

- https://github.com/QwenLM/Qwen3.6
- https://github.com/ollama/ollama/issues/14545
- https://github.com/unslothai/unsloth/pull/5257

### 3. Gemma 4 12B — VERDICT: Corrected in our favor (license is Apache 2.0)

Model real (released June 3, 2026; Gemma 4 family launched April with
E2B/E4B/26B-A4B/31B). VRAM: official table says 6.7GB for Q4_0 weights
(7-8GB total to run with KV cache). Unsloth support first-class; official QAT
variants exist for all five sizes. LICENSE: Gemma 4 is NOT under the custom
"Gemma Terms of Use" — it is the first Gemma generation under OSI-approved
Apache 2.0 (Google Open Source blog + HF card + ai.google.dev). No
prohibited-use policy, no derivative/commercial restrictions beyond standard
Apache. The old Gemma Terms with "Model Derivatives" clauses apply to Gemma <=3
only.

- https://opensource.googleblog.com/2026/03/gemma-4-expanding-the-gemmaverse-with-apache-20.html
- https://ai.google.dev/gemma/terms
- https://ai.google.dev/gemma/docs/core
- https://unsloth.ai/docs/models/gemma-4/train

### 4. Gemma 4 26B-A4B MoE — VERDICT: Confirmed with corrections

Real: 25.2B total / 3.8B active (128 experts, 8 active + 1 shared), 256K
context, Apache 2.0, official QAT checkpoints (14.4GB Q4_0) plus a dedicated
MTP drafter GGUF (~460MB). Speed claim slightly optimistic: best documented is
100.6 tok/s on a 12GB RTX 4070 (QAT UD-Q4_K_XL + MTP drafter, 2.61x over
baseline) — ~100 not ~120 tok/s, and requires f16 KV cache (Q8_0 KV kills MTP
acceptance). Unsloth verbatim: "31B QLoRA works with 22GB and 26B-A4B LoRA
needs >40GB"; Unsloth recommends 16-bit LoRA (not QLoRA) for the MoE.
Practical: great inference target, poor budget fine-tuning target.

- https://ai.google.dev/gemma/docs/core/model_card_4
- https://unsloth.ai/docs/models/gemma-4/train
- https://carteakey.dev/blog/gemma-4-26b-qat-mtp/

### 5. MTP inference support — VERDICT: Shipped; corrected for Apple Silicon

llama.cpp merged generic MTP speculative decoding May 16, 2026 (PR #22673,
tested on Qwen3.6, ~75% acceptance, >2x on CUDA; `--spec-type draft-mtp`) and
Gemma 4 external-drafter MTP June 7 (PR #23398). Ollama shipped Gemma 4 MTP via
its MLX runner on macOS (PR #15980; v0.31 on by default, "~90% faster" on their
benchmark). CAVEAT: in llama.cpp on Metal, MTP is currently a NET SLOWDOWN at
every tested configuration (issues #23752, #23011) — Metal's
compute-to-bandwidth ratio makes K-token verify expensive. MLX-native stacks do
gain on Mac (1.2-1.4x for Qwen at K=1-2; Ollama-MLX Gemma path best). Plain
GGUF is fine: fused Metal Gated DeltaNet kernels landed (PRs #20361/#20340);
Qwen3.5-9B Q4_K_M ~61 tok/s on M4 Max.

- https://github.com/ggml-org/llama.cpp/pull/22673
- https://github.com/ollama/ollama/pull/15980
- https://github.com/ggml-org/llama.cpp/issues/23752
- https://github.com/ggml-org/llama.cpp/pull/20361

### 6. QLoRA cost/time (8-12B, 10-50k examples @ ~4k seq) — VERDICT: Confirmed

Dataset is 40M-200M training tokens/epoch. RTX 4090: ~14-32k tok/s with Unsloth
on 8B => 1-4h per epoch; 3-epoch 50k-example job ~3-12h; at $0.37-0.69/hr
that's ~$1-8. Single H100 (~$2-3/hr): 2-3 epochs in ~1-5h, ~$5-20. Real-world:
Andy-4.2 trained in 5h on one RTX 3090 (2,748 examples). Planning correction:
for Qwen3.5 specifically, Unsloth advises AGAINST 4-bit QLoRA (hybrid-arch
quantization error) — bf16 LoRA for the 9B needs ~22GB, so rent 24GB+ cards.
Gemma 4 12B has no such caveat.

- https://unsloth.ai/docs/models/qwen3.5/fine-tune
- https://mindcraft-ce.com/andy/

### 7. Overlooked candidates — top picks

1. **Ministral 3 8B/14B** (Mistral, Dec 2, 2025) — strongest overlooked fit.
   Apache 2.0 family, base/instruct/reasoning variants, native function
   calling + JSON output, 256k context, plain dense transformer (painless
   QLoRA, no hybrid-arch caveats). llama.cpp merged Dec 1, 2025; ~98 tok/s
   (8B Q4_K_M) / ~58 tok/s (14B) on M5 Max. Family explicitly built by
   "Cascade Distillation" — designed as distillation students
   (arXiv 2601.08584). Prefer Instruct over Reasoning variants for agents.
2. **NVIDIA Nemotron 3 Nano 30B-A3B** (Jan 28, 2026) — purpose-built agentic,
   hybrid Mamba-MoE, 3.2B active, 1M context, reasoning toggle, NVIDIA Open
   Model License (permissive). Runs llama.cpp/LM Studio, trains in Unsloth.
   Downside: ~20GB at Q4 — fine on the Studio, marginal on 12-16GB GPUs.
3. **Qwen3.5-4B** — same license/arch/tooling as the 9B; "lightweight agent"
   positioning; bf16 LoRA trains in ~10GB. The cheap ablation if 9B works.

Ruled out: no small dense Llama exists (Llama 4+ = big MoE, community
license); "Phi-5" has no primary source (newest real Phi: Phi-4-reasoning-
vision-15B, MIT, 16k ctx — poor fit); Mistral Small 3.2 (24B) above the
speed/size envelope.

- https://mistral.ai/news/mistral-3/
- https://arxiv.org/html/2601.08584v1
- https://research.nvidia.com/labs/nemotron/Nemotron-3/

### 8. Distillation-student evidence for agentic/tool use — VERDICT: Evidence exists

- **distil labs benchmark** (15 models x 9 tasks incl. tool calling): Qwen3
  family dominates as students — Qwen3-8B #1 overall, Qwen3-4B-Instruct-2507
  #2 (matches a 120B+ teacher on 8/9 tasks); Llama-3.1-8B/3.2-3B next.
  https://www.distillabs.ai/blog/what-small-language-model-is-best-for-fine-tuning/
- **SOD** (arXiv 2605.07725): on-policy distillation for tool-integrated
  reasoning fails via cascading tool-call errors; step-wise divergence-weighted
  distillation fixes it (up to +20.9% over baselines).
- **SmartAD** (Findings of ACL 2026): capacity-aligned agent distillation —
  pick teacher trajectory with minimum student NLL; up-weight action-execution
  and final-decision spans over intermediate reasoning; beats uniform-loss SFT
  for small students. https://aclanthology.org/2026.findings-acl.1349/
- **Practical caveats:** positive-only tool data destroys refusal behavior
  (include "no-tool" negatives); use Instruct rather than Base variants for
  mixed text+command output.

---

## Material corrections (should change the shortlist)

1. **Drop "Qwen3.6-9B-class" — it does not exist.** The small agentic tier is
   Qwen3.5 (0.8B-9B), already on the list.
2. **Gemma 4 license concern is void — genuine Apache 2.0.** No longer a
   tiebreaker against Gemma 4 12B.
3. **Demote Gemma 4 26B-A4B as a training target** (LoRA needs >40GB; QLoRA
   not recommended on the MoE). Keep as inference-only comparison.
4. **Qwen3.5-9B trains as bf16 LoRA, not QLoRA** (~22GB; rent 24GB+ GPUs).
5. **Don't budget MTP speedups on the Mac via llama.cpp/GGUF** — currently a
   net slowdown on Metal. Plan plain GGUF (~61 tok/s for Qwen3.5-9B Q4 on
   M4 Max) or the Ollama-MLX Gemma path. On NVIDIA, MTP works (>=2x).
6. **Add Ministral 3 8B/14B to the shortlist**; benchmark Nemotron 3 Nano
   30B-A3B if a ~20GB footprint is acceptable.
7. **Training-technique notes for the SFT plan:** up-weight action spans
   (SmartAD), consider divergence-weighted distillation (SOD), include
   no-tool negatives, fine-tune Instruct variants.
