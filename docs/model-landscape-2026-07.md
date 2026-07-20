# Model landscape for Minecraft agents — July 2026

Research snapshot for teacher/student selection (sources: MineExplorer
arXiv:2605.30931, MineNPC-Task arXiv:2601.05215, Mindcraft-CE/Andy HF
cards, Artificial Analysis index reporting, provider announcements).

## 1. Minecraft-agent SOTA

- **MineExplorer** (Meituan, 2026) is the current open-world benchmark for
  Minecraft MLLM agents. Best performers: Claude Opus 4.6 (~78) and
  Gemini 3.1 Pro; ALL models degrade sharply on multi-hop tasks with
  hidden prerequisites. Larger models/thinking modes do NOT consistently
  help. (Vision-based; our stack is text-state, so directional only.)
- **MineNPC-Task** (2026): memory-aware co-play benchmark; ~33% subtask
  failure for GPT-4o-class agents; identifies memory scaffolding as the
  binding constraint — which matches our observed failure modes and
  validates the journal/site-anchor/chest investment.
- Research takeaway: **scaffolding quality rivals model quality** on
  long-horizon Minecraft play. Nobody has solved multi-hop; a stable
  harness + curated data is a real edge, not a consolation prize.

## 2. The Andy line (closest competitor)

- Andy-4.2: 9B, **Qwen3.5 base**, trained on **2,748 examples** in 5 GPU
  hours (QLoRA 4-bit + 8-bit QAT, single 3090). First local model to get
  full diamond armor unattended. Documented weakness: building/newAction
  (token spirals). Andy-5 planned on a new base family.
- Implication: our corpus (17.9k raw steps after 3 days; targeting
  10-50k *curated* steps) is 5-20x Andy's dataset. Their own retro:
  "collect better training data" — exactly the mcft thesis.

## 3. Teacher candidates

| Model | Class | Agentic standing | $/MTok in/out | Distill-OK? |
|---|---|---|---|---|
| Claude Fable 5 | closed | AA Index #1 (60); best hard coding/judgment | $10/$50 | No (personal-use lane only) |
| GPT-5.6 Sol | closed | Agents' Last Exam #1 (53.6, +13 over Fable); best $/agent-run | $5/$30 | No |
| Gemini 3.1 Pro | closed | strong MineExplorer; 2M ctx; weak agentic-coding index | ~$2.50 | No |
| **Kimi K3** | **open (weights 2026-07-27)** | AA ~57, **#3 overall** — within 3 pts of Fable 5 | API now; self-host later | **Yes** |
| GLM-5.2 | open (MIT) | top open-weight deployable today; agentic-focused | cheap API / self-host | Yes |
| DeepSeek V4 Pro | open (MIT) | best price/perf (~$0.04/task) | ~$0.44/$0.87 | Yes |
| qwen3.6:35b local (current) | open | mid-tier; free; validated in our harness | $0 | Yes |

**Headline: the open/closed gap has nearly closed.** Kimi K3 sits between
GPT-5.6 Sol and Opus 4.8 on independent indexes and its weights land
July 27. A frontier-class, distillation-permissive teacher now exists.

## 4. Student candidates

| Model | Size | Notes |
|---|---|---|
| Qwen3.5-9B | 9B dense | Andy-4.2's base — proven for this exact task; Apache 2.0 |
| Qwen3.6 small tier | 0.8-9B | newer gen "optimized for agentic workflows"; Apache 2.0 |
| Gemma 4 12B | 12B dense | best VRAM/$ (6.8GB Q4); Unsloth first-class; QAT variants ship official |
| Gemma 4 26B-A4B | MoE, 4B active | 120 tok/s on 12GB GPU w/ QAT+MTP; strong show-latency choice |
| Qwen3.6-35B-A3B | MoE, 3B active | our current teacher; 73.4% SWE-V at 3B active; could be its own student |

Community signal: Qwen3.5-9B beats Gemma 4 12B on 5 of 8 benchmarks;
Gemma's edge is deployment tooling. Both QLoRA on 24GB; both export GGUF.

## 5. Recommendation

1. **Now**: keep qwen3.6:35b as the scaffolding-era driver (free,
   validated). Finish clean-run baseline.
2. **Teacher, commercial-optional lane**: adopt **Kimi K3** when weights/
   API access settle (post-07-27); GLM-5.2 as the deployable-today
   fallback; DeepSeek V4 for volume. All provenance-tagged.
3. **Teacher, personal showpiece lane**: Fable 5 for judgment-heavy
   scenario sessions; note GPT-5.6 Sol wins pure agent-run benchmarks at
   ~1/4 the cost if we add a second closed lane.
4. **Judge/filter**: Sonnet 5 batch (~$1.25/day) or DeepSeek V4 Flash.
5. **Student**: shortlist Qwen3.5-9B (Andy parity), Qwen3.6-9B-class, and
   Gemma 4 12B/26B-A4B. Decide by (a) tokens/sec on the Studio at our
   16k ctx, (b) Unsloth QLoRA run cost, (c) eval-battery scores after a
   pilot fine-tune on ~5k curated steps. QAT before GGUF export (Andy
   validated this path).
