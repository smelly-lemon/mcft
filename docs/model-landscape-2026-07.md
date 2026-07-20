# Model landscape for Minecraft agents — July 2026 (v2, subagent-validated)

Research snapshot for teacher/student selection. v1 claims were independently
re-verified by three research subagents on 2026-07-20 against primary sources
(license texts, provider ToS, HF cards, llama.cpp/Ollama PRs, arXiv). Full
reports: `validation-teacher-2026-07.md`, `validation-student-2026-07.md`,
`validation-landscape-2026-07.md`. Corrections from validation are marked
**[corrected]**.

## 1. Minecraft-agent SOTA

- **MineExplorer** (Meituan, arXiv 2605.30931): Claude Opus 4.6 best (77.7
  single-hop), Gemini 3.1 Pro second (74.2); ALL models collapse on multi-hop
  (best 23.9). "Larger models or thinking modes do not consistently translate
  into better performance" (verbatim). **[corrected]** It evaluates vision
  MLLMs only and explicitly excludes text-only models — it is NOT a runnable
  target for our stack. Our published comparisons should be **MineCollab**
  (native to the Mindcraft codebase) and **MCU-Turbo** (CraftJarvis).
- **MineNPC-Task** (arXiv 2601.05215): ~33% subtask failure, but
  **[corrected]** that is a GPT-4o-only snapshot with no ablations — use it as
  a failure taxonomy (code execution, inventory, referencing, navigation),
  not a SOTA number. Memory-scaffolding need is hedged in the paper, though it
  still matches our observed failure modes.
- **Cooperation literature** (MineCollab, PillagerBench, VillagerAgent,
  MineLand, Project Sid): converges on **communication efficiency as the
  binding constraint** (~15% drop when agents must communicate detailed
  plans). Key result for us: MineCollab's fine-tuned LLaMA-8B-SFT (0.23)
  nearly matched LLaMA-70B prompted (0.24) — direct published support for the
  distill-a-small-model plan. Make **inter-bot message economy an explicit
  eval metric**.
- Research takeaway unchanged: **scaffolding quality rivals model quality**;
  nobody has solved multi-hop; a stable harness + curated data is a real edge.

## 2. Competitive landscape

- **Andy-4.2** (validated in full): 9B on Qwen3.5, 2,748 examples, 5 GPU-hours
  (QLoRA 4-bit + 8-bit QAT, one 3090). First local model to full diamond armor
  unattended. Weakness verbatim: !newAction "would produce thousands and
  thousands of tokens, but never do anything." Their stated next step:
  "collect better training data" — the mcft thesis. **No other serious
  Mindcraft fine-tune exists.**
- **Prior art for the show** **[new]**: crypto projects **ClaudeCraft** (three
  Claude bots co-building 24/7, $CRAFT memecoin, viewer bounties — now
  apparently defunct) and **CLAUDEMINE** ($MINE, single-agent Kick stream)
  partially occupy "paid viewer influence over AI builders." Neuro-sama
  remains the only large monetized AI streamer in Minecraft (one persona,
  plays with humans). Open-source copycat risk: JesseRWeigel's
  minecraft-agent-swarm (multi-bot, local LLM, Twitch !goal/!vote, OBS/TTS).
  **Differentiation thesis: qualified but intact** — the unoccupied slot is
  platform-native monetization + steerable personas + measured reliability.
- **Willingness to pay is proven** **[new]**: MinePal ($2.99-13.99/mo,
  Mindcraft-lineage) and NeverPlayAlone (hosted AI worlds, $9-29/mo) are
  shipping companion/hosting products.
- Upstream framework renamed: mindcraft-bots/mindcraft (5.5k stars, MIT);
  mindcraft-ce is the active community fork. Still the dominant scaffold.

## 3. Teacher candidates

| Model | Class | Agentic standing | $/MTok in/out | Distill lane |
|---|---|---|---|---|
| DeepSeek V4 Pro | open (MIT) | mid-frontier; Vending-Bench 2 mid-pack | $0.435/$0.87 | **Only API with an explicit written distillation grant** ("training other models (such as model distillation)" permitted, ToS 4.2) |
| GLM-5.2 | open (MIT) | best open on Vending-Bench 2 ($8.3k) + AA open-weight #1 | self-host or 3rd-party host | **[corrected]** Z.ai API bans ALL external-model training — MIT weights clean, so **self-host only** |
| Kimi K3 | open? (weights promised 07-27) | AA 57.1, #3 family; #1 AutomationBench-AA | $3/$15 API | **[corrected]** License NOT yet announced ("Modified MIT" was speculation); API ToS has a broad competitive-use ban and no distillation grant. **Wait for the actual LICENSE file.** |
| Nemotron 3 Ultra **[new]** | open (OpenMDW-1.1) | agent-focused 550B/55B-active; trails GLM-5.2 | self-host | **Most distillation-friendly license in existence** — zero output restrictions, explicitly permits competing models; NVIDIA ships training data + recipes |
| Inkling (Thinking Machines) **[new]** | open (Apache 2.0) | AA ~41; MCP Atlas 74.1% | self-host / Tinker | Clean (Apache 2.0); leading US open-weights option |
| Claude Fable 5 | closed | AA #1 (59.9) BUT **[corrected]** underperforms on Vending-Bench 2 long-horizon coherence at every reasoning effort (~$4.3-5.7k vs Opus 4.7's $10.9k) | $10/$50 | No — and the clause is keyed to "competing," **not conditioned on commercial use** |
| GPT-5.6 Sol | closed | Agents' Last Exam #1 (52.7 table / 53.6 max-config); τ³-Banking #1 | $5/$30 | No (same competing-model clause) |
| Gemini 3.1 Pro | closed | **[corrected]** $2.00/MTok in, 1M ctx (not $2.50/2M); weak agentic indexes | $2/$12 | No |
| qwen3.6:35b local (current) | open (Apache 2.0) | mid-tier; free; validated in our harness | $0 | Yes |

**Revised headline:** the open/closed gap has nearly closed, but the two
"clean-teacher" bets shifted under validation. K3 is unproven AND unlicensed
until 07-27; the deployable-today clean lanes are **DeepSeek V4 Pro via API**
(explicit grant, cheapest) and **GLM-5.2 self-hosted** (best open long-horizon
coherence, but requires ~40B-active serving infra). Fable 5 lost its teacher
case twice over: ToS applies regardless of monetization, and it is empirically
weak at exactly the capability we need (long-horizon coherence).

## 4. Student candidates

| Model | Size | License | Notes |
|---|---|---|---|
| Qwen3.5-9B | 9B hybrid (Gated DeltaNet) | Apache 2.0 | Andy-4.2's base — proven for this task. **[corrected]** Unsloth advises bf16 LoRA, NOT QLoRA (hybrid-arch quant error); ~22GB to train. ~61 tok/s Q4 GGUF on M4 Max |
| Gemma 4 12B | 12B dense | **[corrected] Apache 2.0** (first Gemma under OSI license — old "Gemma Terms" fear is void) | 6.7GB Q4 weights; first-class Unsloth QLoRA; official QAT variants |
| Ministral 3 8B/14B **[new]** | dense | Apache 2.0 | Explicitly built by "Cascade Distillation" as student models; native function calling; painless QLoRA; ~98/58 tok/s on Apple Silicon. Use Instruct variants |
| Qwen3.5-4B | 4B | Apache 2.0 | Cheap ablation; distil-labs benchmark ranks Qwen3-4B-class #2 student overall |
| Gemma 4 26B-A4B | MoE 3.8B active | Apache 2.0 | **[corrected]** DEMOTED to inference-only: LoRA needs >40GB, QLoRA not recommended on the MoE. ~100 tok/s (not 120) on 12GB w/ QAT+MTP, f16 KV required |
| ~~Qwen3.6 small tier~~ | — | — | **[corrected] Does not exist.** Qwen3.6 = 27B dense + 35B-A3B only |

Also on radar: Nemotron 3 Nano 30B-A3B (agentic specialist, ~20GB Q4 — fine on
the Studio, marginal on consumer GPUs).

Distillation-student evidence **[new]**: distil-labs' 15-model benchmark has
the Qwen3 family #1-2 as fine-tuning students for tool calling; SOD
(arXiv 2605.07725) and SmartAD (ACL 2026) both say up-weight action/decision
spans over reasoning spans and prefer divergence-weighted distillation;
include "no-tool" negatives to preserve refusal behavior; fine-tune Instruct,
not Base.

Mac deployment note **[corrected]**: do NOT budget MTP speedups via
llama.cpp/GGUF on Apple Silicon (currently a net slowdown on Metal); plain
GGUF or Ollama's MLX path (Gemma 4 MTP ~1.9x there) are the realistic routes.
On NVIDIA, MTP delivers >=2x as advertised.

## 5. Recommendation (revised after validation)

1. **Now**: keep qwen3.6:35b as the scaffolding-era driver (free, validated).
   Finish clean-run baseline.
2. **Teacher, default clean lane**: **DeepSeek V4 Pro API** — the only
   provider with an explicit written distillation grant, at $0.435/$0.87.
   Provenance-tag everything.
3. **Teacher, quality clean lane**: **GLM-5.2 self-hosted** (rented GPU or
   MIT-licensed third-party host; NEVER the Z.ai API) — best open-weight
   long-horizon coherence on record.
4. **Kimi K3**: hold until weights + actual LICENSE ship (promised 07-27),
   then re-evaluate. Do not run K3-teacher datagen through Moonshot's API.
5. **Fable/GPT lane**: demoted from "teacher" to **judge/curator and
   scenario-writer** duties. Rationale: closed-model ToS bans are not
   conditioned on commercial use, and Fable 5 measurably underperforms on
   long-horizon coherence. Sonnet 5 batch (~$1.25/day) or DeepSeek V4 Flash
   for the judge/filter lane.
6. **Student**: shortlist **Qwen3.5-9B** (bf16 LoRA), **Gemma 4 12B** (QLoRA),
   **Ministral 3 8B** (QLoRA) — all Apache 2.0. Decide by (a) tok/s on the
   Studio at 16k ctx, (b) fine-tune run cost (~$5-30/run on rented GPU, hours
   not days), (c) eval-battery scores after a pilot fine-tune on ~5k curated
   steps. QAT before GGUF export (Andy validated this path).
7. **SFT recipe adjustments**: up-weight action-emission spans, include
   no-tool negatives, train on Instruct bases, and track inter-bot message
   economy as a first-class eval metric (MineCollab shows 8B-SFT can match
   70B-prompted on cooperation).
