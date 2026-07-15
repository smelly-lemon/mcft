# datagen — trajectory-to-SFT pipeline (design)

Stages: ingest -> episode filter -> step windowing -> loss-target selection ->
persona handling -> deliberation policy -> provenance stamp -> dedup -> split.

Bootstrap (where the first data comes from): a strong open-weight driver is
the PRIMARY trajectory generator — Qwen3.5-35B-A3B-class MoE (Apache-2.0,
~3B active params, runs fast on the Studio) plays via Mindcraft under each
persona in rotation. Collection rides on the attended show-prototype
sessions (roadmap steps 1-4): the same driver, personas, and logger that
make the show also make the dataset — data collection is never a separate
grind. Rationale: every comparable project (FireAct,
AgentTuning, MineCollab, Andy-4.2) bootstrapped from a strong driver; even a
70B driver succeeded at only ~10-25% of MineCollab trials, so weak-model
self-play would take weeks to produce a biased-easy dataset. The student
model's own episodes are mixed in later, once it succeeds at a useful rate
(natural rejection-sampling loop). Volume target: quality over quantity —
low thousands of well-filtered windows (~100-300 kept episodes) is the first
useful checkpoint (Andy-4.2 shipped on 2,748 examples). Early episodes are
hand-reviewed before anything is trained on. No Andy derivatives, no
closed-API output, ever (ADR-0003).

Episode filter (recovery-aware): keep episodes with outcome == success —
including messy wins that contain failed steps — AND episodes that ultimately
failed but contain a failed execution_result followed within 6 steps by a
successful execution of a related action ("recovered failures"; only the
recovery segment is windowed from these). Success-only filtering strips
recovery skill; recovered failures are some of the most valuable data we
have.

Loss-target selection: only steps with step_type in {chat, command, code}
become assistant targets — and a step whose execution_result failed is NEVER
a target. Failed steps appear only as context, so the model learns to recover
from mistakes without learning to make them.

Step windowing: context = assembled system prompt (persona) + a rolling
window of prior turns reconstructed from model_input/model_output.

Personality comes from two sources:
1. Organic per-persona trajectories (primary): the bot actually runs each
   persona, so goal selection, pacing, and chat style vary genuinely between
   personas. Behavioral persona differences are legitimate and desired, as
   long as the action contract is respected.
2. Synthetic chat rewrites (augmentation only): kept trajectories are
   duplicated across K personas by rewriting CHAT content only, via the
   open-weight teacher. Command/code steps are never rewritten (the action
   contract is invariant); rewrites cannot create behavioral personality and
   are not asked to. Rewrites get source=synthetic_rewrite and full
   Provenance including source_episode_id and pipeline_version.

Deliberation policy: per ADR-0004 — SLOW/FAST mode is a property of the
REQUEST, chosen by the bot loop and recorded at logging time; datagen labels
each example with the recorded mode. SLOW targets are filtered/truncated to
the reasoning-token budget so the model learns short deliberation. Datagen
enforces a TARGET MIX RATIO (starting point 60-75% SLOW-labeled, per Unsloth
guidance for preserving dual-mode capability) by rebalancing — never
whatever ratio the logs happen to contain (organic logs skew FAST).
Serialization follows the base model's chat template exactly; loss on
assistant tokens only; reasoning content is not carried into
subsequent-turn history.

Preference-pair hook (design only, post-SFT-v1): datagen should be able to
emit (chosen, rejected) pairs for offline DPO from same-task/same-state
success/failure steps — execution_result and reward_signals already carry
what's needed. No reward model, no online RL; DPO is operationally identical
to SFT and targets the failure modes SFT won't fix (repetition loops,
precondition neglect).

Dedup: sha256 over (persona_id + whitespace-normalized, case-preserved
messages). Case is persona signal (Jolt shouts); never lowercase.

Split: by sha256(episode_id) into 95/5 train/val — never split within an
episode. The stdlib hash() is process-randomized and must not be used. Once
volume permits, hold out entire episodes/tasks as Split.TEST, never trained
on.
