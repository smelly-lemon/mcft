# Minecraft Competitive-Landscape Validation Report — July 20, 2026

Independent verification of the research doc's Minecraft-agent claims plus a
fresh competitive scan (subagent-run, primary sources: arXiv, GitHub, HF cards,
project sites).

---

## Claim-by-claim verification

### 1. MineExplorer — VERDICT: Confirmed (with framing caveats)

arXiv 2605.30931 real (Meituan LongCat + SJTU). Claude-Opus-4.6 best
(single-hop task success 77.7), Gemini-3.1-Pro-Preview second (74.2); every
model collapses on multi-hop (best multi-hop TSR 23.9). "Larger models or
thinking modes do not consistently translate into better performance" is
verbatim from the abstract. Caveats: it is brand-new (May 2026) — MCU/MCU-Turbo
(ICML 2025, CraftJarvis) is the other standard — and MineExplorer EXPLICITLY
EXCLUDES text-only models (vision MLLMs on frame buffers), so it cannot be run
against a text-only Mindcraft bot.

- https://arxiv.org/abs/2605.30931
- https://github.com/meituan-longcat/MineExplorer

### 2. MineNPC-Task — VERDICT: Confirmed (with one softening)

arXiv 2601.05215 checks out: memory-aware, mixed-initiative co-play benchmark
on public Mineflayer APIs; GPT-4o snapshot, 8 expert players, 44 tasks / 216
subtasks, 71 failures ~ 33%; failures in code execution, inventory handling,
referencing, navigation. Softening: the paper hedges ("consistent with the
need for stronger memory scaffolding") — it does not declare memory THE
binding constraint, and it is a single-model snapshot with no ablations. Use
as a failure taxonomy, not a SOTA number.

- https://arxiv.org/abs/2601.05215

### 3. Andy-4.2 — VERDICT: Confirmed

HF card + mindcraft-ce.com match every detail: 9B on Qwen3.5 (Gated DeltaNet),
2,748 examples, 5h on one RTX 3090, QLoRA 4-bit + 8-bit QAT, "first local
model capable of getting a full set of diamond armour, with zero human
interaction" verbatim. Limitations confirm the building weakness: !newAction
"would produce thousands and thousands of tokens, but never do anything."
"What's Next" confirms "collect better training data." Variant family:
Andy-4.2-Micro, -Air, Andy-4.20 (XML tool calling).

- https://huggingface.co/Mindcraft-CE/Andy-4.2
- https://mindcraft-ce.com/andy/

### 4. Mindcraft dominance — VERDICT: Confirmed (naming correction)

Upstream renamed kolbytn/mindcraft -> mindcraft-bots/mindcraft (5,505 stars,
MIT, last push June 2026; backed by the "Collaborating Action by Action"
paper). mindcraft-ce/mindcraft-ce is the actively developed community fork
(dataset-collection tooling, plugin system). No comparable community scaffold
exists — Voyager unmaintained since April 2024, research-only. The commercial
product MinePal is itself a Mindcraft-lineage fork.

- https://github.com/mindcraft-bots/mindcraft
- https://github.com/mindcraft-ce/mindcraft-ce
- https://arxiv.org/abs/2504.17950

### 5. Competitive scan

- **Academic (mostly research-only):** Voyager (dead), CraftJarvis ecosystem
  (JARVIS-1, MineStudio, MCU/MCU-Turbo), STEVE family (MrSteve, WISE arXiv
  2606.12852), JARVIS-VLA, MineDreamer, Echo (CVPR 2026). Only near-deployable
  academic agent: Optimus-3 (v2 + MineSys2, March 2026) — needs 28-32GB VRAM,
  vision-based, not a streamable companion. None run on Mineflayer text
  scaffolds; none are products.
- **Commercial/streaming:** Neuro-sama remains the only large monetized AI
  streamer playing Minecraft (hardcore completion Dec 9, 2025 after 87
  attempts, with 3 human streamers). Crypto-token 24/7 streams appeared early
  2026: **ClaudeCraft** (three Claude bots cooperatively building, 24/7
  stream, $CRAFT memecoin, viewer build-bounties/wagers/tips) and
  **CLAUDEMINE** ($MINE, single-agent 24/7 Kick stream, chat suggestions).
  Open-source blueprint: JesseRWeigel's minecraft-agent-swarm (5-bot swarm on
  local gpt-oss:20b, OBS overlays, TTS, Twitch !goal/!vote — not monetized).
  Altera's Project Sid team pivoted away (Fundamental Research Labs);
  Regression Games pivoted to Unity QA.
- **Paying-customer companion products:** MinePal ($2.99-13.99/mo, Mindcraft
  fork); NeverPlayAlone (hosted AI-agent worlds + "Genie" admin, free/$9/$29
  per month — bot-hosting-as-a-service, live now); Questie AI ($19.99/mo
  voice companion); Nova/Quantum (free Fabric mod).
- **Other Mindcraft-compatible fine-tunes:** essentially none of significance
  (i6od/mindcraft-lora ~3 downloads; older Sweaterdog experiments). The Andy
  family has no serious fine-tune competitor.

### 6. Monetized "multi-bot cooperative build, viewers influence goals"

No established incumbent; crypto experiments partially occupy it. Closest:
ClaudeCraft — literally viewers paying (via token/bounties) to influence
multi-bot builds — but it is a Feb 2026 hackathon/memecoin project (token near
zero, site 403s, no personas, no Twitch presence; operational status
unverifiable). Neuro-sama is genuinely monetized with huge Minecraft
viewership but is one AI persona playing with humans. Conclusion: the
differentiation thesis HOLDS for a platform-native (Twitch/YouTube),
persona-steerable, reliability-measured show — but "nobody has done paid
viewer influence over cooperating AI builders" is no longer strictly true;
name the crypto projects as prior art.

- https://github.com/888BasedGod-sol/Claudecraft
- https://www.claudemine.com/

### 7. Multi-agent LLM cooperation in Minecraft — published work

- **MineCollab / MINDcraft** (arXiv 2504.17950, same team as the framework):
  primary bottleneck is EFFICIENT NL COMMUNICATION — performance drops ~15%
  when agents must communicate detailed plans; degrades with agent count.
  Fine-tuned LLaMA-8B-SFT (0.23) nearly matched LLaMA-70B prompted (0.24);
  Claude-3.5-Sonnet led (0.49). "LLM agents are ill-optimized for multi-agent
  collaboration." https://mindcraft-minecollab.github.io/
- **PillagerBench + TactiCrafter** (IEEE CoG 2025): explicit human-readable
  tactics + learned causal model + opponent modeling beat CoT baselines.
- **VillagerAgent** (ACL Findings 2024): DAG-based task decomposition reduces
  hallucination vs free-form coordination.
- **TeamCraft** (arXiv 2412.05255): fine-tuned VLA baselines fail to
  generalize to novel goals/scenes/agent counts.
- **MineLand** (arXiv 2403.19267): restricted perception forces communication;
  cooperation cuts per-agent workload at communication overhead cost.
- **Project Sid (PIANO):** role specialization only emerged with social
  awareness of others' goals.
- **Synthesis:** cooperation works when communication is short and structured,
  tasks are explicitly decomposed with roles/dependencies, plans are
  externalized in readable form, and agents track commitments in memory.
  Fine-tuning on collaborative trajectories is the documented lever that
  lifts small models to large-model cooperation levels.

---

## Material corrections/additions (should change strategy)

1. **Differentiation thesis: qualify, don't retire.** ClaudeCraft/CLAUDEMINE
   already monetized viewer influence over AI Minecraft builders via
   memecoins. The unoccupied slot is narrower but real: platform-native
   monetization + steerable personas + measured reliability.
2. **Benchmark-target correction:** MineExplorer excludes text-only models.
   MineCollab (native to the Mindcraft codebase) and MCU-Turbo are the right
   published comparisons for our stack.
3. **Bot-hosting-as-a-service already exists** (NeverPlayAlone, MinePal) —
   incumbents for that product direction, and proof of willingness to pay.
4. **Inter-bot message economy should be an explicit eval metric** — the
   cooperation literature converges on communication efficiency as the
   binding constraint; MineCollab's 8B-SFT ~ 70B-prompted result directly
   supports the fine-tuning plan.
5. **Watch minecraft-agent-swarm** (JesseRWeigel) — open-source replica of
   much of the show stack (multi-bot, local LLM, Twitch voting, OBS/TTS);
   lowers the copycat barrier.
6. **Don't generalize MineNPC-Task's 33%** — GPT-4o-only snapshot; treat as a
   failure-taxonomy source (code execution, inventory, referencing,
   navigation) for our eval battery.
