# Teacher-Model Claim Validation Report — July 20, 2026

Independent verification of the research doc's claims about candidate distillation
teacher models, with emphasis on licensing for a commercially-clean data lane.
All claims were checked against primary sources (license texts, provider terms of
service, official pricing pages, and benchmark publishers) via web search on
July 20, 2026.

---

## Claim-by-claim verification

### 1. Kimi K3 release / specs / ranking — VERDICT: Confirmed (minor nuance on rank)

Released July 16, 2026 via API/apps only; Moonshot's own blog commits to full
weights "by July 27, 2026." Artificial Analysis measured 57.1 on Intelligence
Index v4.1 — AA's own headline calls it "#3," behind Claude Fable 5 (59.9) and
GPT-5.6 Sol (58.9); it is #4 if you count Sol's two reasoning configurations
separately. AA explicitly calls it "comparable to Opus 4.8 and GPT-5.5," and it
is a 2.8T-param MoE (1M context, ~50B active estimated). API pricing is
$3.00/$15.00 per MTok ($0.30 cache hit).

**Correction:** none material; "ranked #3 overall" is AA's model-family framing,
#4 by tested configuration.

Sources:

- https://www.kimi.com/en/blog/kimi-k3
- https://artificialanalysis.ai/articles/kimi-k3-achieves-3-in-the-artificial-analysis-intelligence-index-comparable-to-opus-4-8-and-gpt-5-5
- https://artificialanalysis.ai/models

### 2. Kimi K3 license (CRITICAL) — VERDICT: Corrected

K3's license is **not announced** as of July 20, 2026 — no repository, no
LICENSE file, no named license exists yet. "Modified MIT" is only an expectation
projected from K2.x precedent and should not be treated as settled.

On the K2-series Modified MIT itself: the *only* modification is a UI
attribution requirement ("prominently display 'Kimi K2'") for commercial
products with more than 100M monthly active users or more than $20M *monthly*
revenue — it otherwise grants MIT-style rights "without restriction," so it does
not restrict distillation or output use (distillation is neither mentioned nor
forbidden; a fine-tuned model is arguably a "derivative work" that inherits the
attribution trigger at scale).

The API lane is the problem: the Kimi OpenPlatform Terms of Service (updated
May 27, 2026) contain **no explicit output-training ban but prohibit**
"developing, serving, or creating applications, products, Services, or models
that have potential competitive possibilities with the Services without
authorization" (Section 3.2(5)) — vaguer and arguably broader than
Anthropic/OpenAI's "competing models" clauses — and contain no DeepSeek-style
distillation permission. The terms also let Moonshot use customer content to
improve its own services unless a separate enterprise agreement restricts it.

**Correction:** treat K3 as *unlicensed* until weights + LICENSE actually ship
(promised July 27). Until then K3 is not a commercially-clean distillation
teacher; the API route carries a broad competitive-use prohibition.

Sources:

- https://github.com/moonshotai/Kimi-K2/blob/main/LICENSE (Modified MIT text)
- https://platform.moonshot.ai/docs/agreement/modeluse (Kimi OpenPlatform ToS)
- https://howaiworks.ai/blog/moonshot-kimi-k3-release-announcement (no license named as of July 17)
- https://www.digitalapplied.com/blog/kimi-k3-open-weights-july-27-adoption-readiness-checklist

### 3. GLM-5.2 (Zhipu / Z.ai) — VERDICT: Confirmed on specs; Corrected on API distillation

MIT license confirmed (Zhipu markets it as "Pure Open: An MIT open-source
license"); 744B-A40B MoE (Hugging Face parameter counter shows 753B total),
solid 1M context, SWE-bench Pro 62.1 (self-reported), and it is the current
open-weight leader on the AA Intelligence Index (51.1) and the top open-weight
model on Vending-Bench 2 — "top deployable open-weight agentic model today"
holds while K3 remains API-only.

**However, Z.ai's API Terms of Use flatly prohibit distillation:** "any use of
the Z.ai's models, prompts, or model-generated content for the development,
training, labeling, fine-tuning, optimization, iteration, or similar activities
related to external models is strictly prohibited" (plus a separate ban on
training anything that competes with Z.ai). That bans *all* external-model
training with API outputs, not just competing models.

**Correction:** the MIT weights carry no such restriction, so the clean lane is
**self-hosting the weights** (or a third-party host serving them under MIT),
never the Z.ai API.

Sources:

- https://docs.z.ai/legal-agreement/terms-of-use (see clause xii)
- https://huggingface.co/zai-org/GLM-5.2
- https://docs.z.ai/guides/llm/glm-5.2

### 4. DeepSeek V4 Pro — VERDICT: Confirmed

MIT-licensed weights on Hugging Face ("This repository and the model weights
are licensed under the MIT License"), 1.6T total / 49B active MoE, 1M context.
Official pricing page today: $0.435 input (cache miss) / $0.87 output /
$0.003625 cache hit per MTok — matching the doc's ~$0.44/$0.87 (the launch "75%
promo" became the standard rate after May 31, 2026).

DeepSeek's terms *explicitly permit* distillation: "You may apply the Inputs
and Outputs of the Services to a wide range of use cases, including … derivative
product development, training other models (such as model distillation)"
(Section 4.2 of both the consumer Terms of Use and the Open Platform ToS). This
makes DeepSeek the only major API provider with an affirmative, written
distillation grant.

**Correction:** none.

Sources:

- https://cdn.deepseek.com/policies/en-US/deepseek-open-platform-terms-of-service.html
- https://cdn.deepseek.com/policies/en-US/deepseek-terms-of-use.html
- https://api-docs.deepseek.com/quick_start/pricing
- https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro

### 5. Claude Fable 5 — VERDICT: Confirmed

Anthropic's pricing page: $10/$50 per MTok, cache hits $1/MTok, Batch API 50%
off ($5/$25) — all exact. #1 on AA Intelligence Index at ~60 (59.9, "Adaptive
Reasoning, Max Effort, Opus 4.8 Fallback" configuration, out of 150 models).

The commercial terms clause reads: "Customer may not and must not attempt to
(a) access the Services to build a competing product or service, **including to
train competing AI models** except as expressly approved by Anthropic; … or
(c) support any third party's attempt at any of the conduct restricted in this
sentence." It is **not conditioned on commercial use** — the trigger is
"competing," so even non-commercial training of a competing model violates it.
Anthropic's help center says non-competing specialized models (classifiers,
extractors, etc.) are allowed, but lists "using Outputs as training targets for
models" and "models designed for open-ended text generation" among prohibited
uses — so a game-agent LLM is a gray zone at best without written permission.

**Correction:** none on facts; note the clause is keyed to "competing," not
commercial use.

Sources:

- https://platform.claude.com/docs/en/about-claude/pricing
- https://www-cdn.anthropic.com/471bd07290603ee509a5ea0d5ccf131ea5897232/anthropic-vertex-commercial-terms-march-2024.pdf
- https://support.claude.com/en/articles/12326764-can-i-use-my-outputs-to-train-an-ai-model
- https://artificialanalysis.ai/models

### 6. GPT-5.6 Sol — VERDICT: Confirmed (with two footnotes)

Pricing $5/$30 per MTok confirmed on OpenAI's announcement (footnote 1:
requests over 272K input tokens bill at $10/$45). Agents' Last Exam: OpenAI's
eval **table** lists Sol at 52.7% vs Fable 5's 40.5%; the 53.6 figure is
OpenAI's prose claim for a maxed-out reasoning configuration ("eclipsing Claude
Fable 5 by 13.1 points" — 53.6 − 40.5). Footnote 2: both figures are
OpenAI-reported, not independently audited.

OpenAI's terms prohibition confirmed: customers may not, "except for a
Permitted Exception, use Output to develop artificial intelligence models that
compete with OpenAI's products and services" (Services Agreement Section
3.3(e)); the Permitted Exception covers non-distributed
classifiers/categorizers and fine-tuning OpenAI's own models. Again keyed to
"competing," not commercial use.

**Correction:** none material; cite 52.7 (table) rather than 53.6 (max-config
prose) if precision matters.

Sources:

- https://openai.com/index/gpt-5-6/
- https://openai.com/policies/services-agreement/
- https://openai.com/policies/row-terms-of-use/

### 7. Gemini 3.1 Pro — VERDICT: Corrected

Two factual errors in the research doc:

1. Input price is **$2.00/MTok** for prompts ≤200K tokens ($4.00 above; output
   $12.00/$18.00) — not $2.50.
2. Context is **1M tokens (1,048,576), not 2M**.

"Strong on MineExplorer" is fair: Gemini 3.1 Pro Preview ranks #2 of all tested
models (37.02% overall task success rate, behind Claude Opus 4.6's 41.08%) on
the meituan-longcat MineExplorer Minecraft benchmark (arXiv 2605.30931). "Weak
on agentic indexes" confirmed: AA Intelligence Index 46.5, GDPval-AA v2 Elo 962
(worst among frontier peers), Agents' Last Exam 32.1%.

Google's Gemini API Additional Terms: "You may not use the Services to develop
models that compete with the Services (e.g., Gemini API or Google AI Studio)" —
the same competing-model pattern as OpenAI/Anthropic.

Sources:

- https://ai.google.dev/gemini-api/terms
- https://arxiv.org/html/2605.30931v2 (MineExplorer paper)
- https://devtk.ai/en/models/gemini-3-1-pro/ (pricing tracker, official-pricing sourced)
- https://openai.com/index/gpt-5-6/ (cross-model eval table)

### 8. Other frontier-class open-weight, distillation-friendly models — VERDICT: Yes, two significant ones overlooked

- **Inkling (Thinking Machines Lab, July 15, 2026)** — 975B/41B-active MoE, 1M
  context, **Apache 2.0**, explicitly positioned as a fine-tuning/customization
  base with day-one Tinker support. AA Index ~41 (below GLM-5.2), but credible
  agentic scores (MCP Atlas 74.1%, GDPval-AA v2 1238 Elo) and the cleanest
  license in its class. The leading US open-weights option.
  - https://thinkingmachines.ai/model-card/inkling/
  - https://huggingface.co/blog/thinkingmachines-inkling
- **Nemotron 3 Ultra (NVIDIA, June 4, 2026)** — 550B/55B-active, built
  specifically for long-running agents, licensed **OpenMDW-1.1**, which states
  it "does not impose any restrictions or obligations with respect to any use,
  modification, or sharing of any outputs generated" and explicitly permits
  competing models — the most distillation-friendly license available; NVIDIA
  also ships training data and recipes. Agentic scores trail GLM-5.2
  (GDPval-AA 1164 Elo, τ³-Banking 13.8%).
  - https://developer.nvidia.com/blog/nvidia-nemotron-3-ultra-powers-faster-more-efficient-reasoning-for-long-running-agents/
  - https://github.com/OpenMDW/OpenMDW/blob/main/1.1/LICENSE.OpenMDW-1.1
- **Qwen3.5-397B-A17B (Alibaba, Feb 2026)** — Apache 2.0, agent-focused, 262K
  native context; a legitimate mid-frontier option.
  - https://www.alibabacloud.com/blog/qwen3-5-towards-native-multimodal-agents_602894
- **MiniMax M3 is *not* clean:** its Community License is non-commercial by
  default, requires "Built with MiniMax M3" attribution plus a one-time notice
  email for any commercial use, and requires prior written authorization above
  $20M/year revenue.
  - https://huggingface.co/MiniMaxAI/MiniMax-M3/raw/main/LICENSE
- **Llama is a dead end:** Meta pivoted its frontier effort to the closed Muse
  Spark line in April 2026 and no frontier-class open Llama exists (third-party
  reports of a "Llama 5" conflict with each other; the consistent picture is
  small/mid-size releases at best, under a 700M-MAU-gated community license).
  - https://www.digitalapplied.com/blog/open-weight-models-h1-2026-retrospective-deepseek-qwen-llama

### 9. Published evidence on long-horizon multi-step agentic consistency (non-coding) — VERDICT: Partially answerable; no benchmark matches the exact setup

Nothing published tests "text-only, ~3k-token prompts, short structured
commands" directly, but four relevant bodies of evidence exist:

1. **Vending-Bench 2** (Andon Labs; 365 simulated days of text-based business
   operations — the purest long-horizon coherence test): Claude Opus 4.7 leads
   ($10,937), GPT-5.6 Sol $9,619, **GLM-5.2 $8,314 (best open-weight)**, Kimi
   K2.6 $6,205 — and notably **Claude Fable 5 underperforms at every reasoning
   effort (~$4.3k–5.7k)**, so its AA #1 rank does not transfer to long-horizon
   coherence. Kimi K3 not yet listed.
   - https://andonlabs.com/evals/vending-bench-2
   - https://andonlabs.com/blog/fable5-vending-bench
2. **τ³-Banking** (multi-turn tool-use consistency, part of AA v4.1):
   GPT-5.6 Sol 33.0% > Fable 5 = GLM-5.2 26.8% > DeepSeek V4 Pro 25.8% >
   Inkling 23.7% > Kimi K2.6 20.6% > Gemini 3.1 Pro 16.5%.
   - https://thinkingmachines.ai/model-card/inkling/ (cross-model table)
3. **GDPval-AA v2 / AutomationBench-AA / AA-Briefcase** (long-horizon agentic
   knowledge work): Fable 5 (1760 Elo) and Kimi K3 (1668 Elo; #1 on
   AutomationBench-AA at 53%; #2 on AA-Briefcase) lead; GLM-5.2 1514,
   GPT-5.5 1494, DeepSeek V4 Pro 1307, Gemini 3.1 Pro 962.
   - https://artificialanalysis.ai/articles/kimi-k3-achieves-3-in-the-artificial-analysis-intelligence-index-comparable-to-opus-4-8-and-gpt-5-5
4. **Game-specific:** MineExplorer (multimodal Minecraft ReAct agents; Claude
   Opus 4.6 41.08% and Gemini 3.1 Pro 37.02% on top; every model collapses on
   multi-hop tasks — best is 23.87%) and TextQuests/BALROG (text-only game
   benchmarks structurally closest to this workload, but with no published
   results yet for the July-2026 model crop).
   - https://arxiv.org/abs/2605.30931
   - https://www.textquests.ai/

Net: evidence is mixed and no model dominates. Among *distillation-clean*
teachers, GLM-5.2 (self-hosted) has the strongest long-horizon coherence
evidence; K3 is promising on knowledge-work agentic evals but unproven on
long-horizon coherence and unlicensed until July 27.

---

## Material corrections (should change strategy)

1. **K3's license does not exist yet.** "Modified MIT" is unconfirmed
   extrapolation from K2.x. Until weights + LICENSE actually ship (promised
   July 27), the only K3 lane is Moonshot's API, whose ToS prohibits building
   models with "potential competitive possibilities" and grants no distillation
   permission. Do not schedule K3-teacher datagen through the API; wait for and
   read the actual license file.
2. **You cannot use the Z.ai API for distillation at all.** Zhipu's API terms
   prohibit using outputs for *any* external-model training — broader than the
   "competing models" clauses elsewhere. GLM-5.2's MIT weights are clean, but
   trajectories must come from a self-hosted (or MIT-licensed third-party)
   deployment, which changes the infra cost math.
3. **DeepSeek V4 Pro is the only teacher with an explicit written distillation
   grant in its API terms** ($0.435/$0.87 now standard pricing) — the
   lowest-friction commercially-clean lane and probably the default teacher.
4. **Gemini 3.1 Pro facts were wrong:** 1M context (not 2M) and $2.00/MTok
   input (not $2.50); Google's API terms also carry a competing-model training
   ban.
5. **Fable 5 is weak at exactly the thing this project cares about:** it
   underperforms Opus 4.7, GPT-5.5, and GLM-5.2 on Vending-Bench 2 long-horizon
   coherence at every reasoning effort — its AA #1 ranking shouldn't drive
   teacher choice even before hitting Anthropic's ToS wall.
6. **Two overlooked distillation-friendly options:** Inkling (Apache 2.0, 975B,
   July 15) and Nemotron 3 Ultra (OpenMDW-1.1, zero output restrictions,
   agent-focused). MiniMax M3 should be dropped from the "clean" list — its
   license is non-commercial by default with revenue-gated authorization.
