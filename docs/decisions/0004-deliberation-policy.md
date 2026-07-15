# ADR-0004: Deliberation policy (FAST/SLOW)

**Context.** A reasoning model that thinks before every utterance pays a
latency tax a real-time bot can't afford; vendors' thinking-toggle
mechanisms churn between model generations.

**Decision.** Deliberation is a property of the *request*, decided by the
bot loop and logged per step — never decided by the model mid-generation.
Defined behaviorally, not in terms of any vendor's chat-template toggle, so
it survives a base-model change. Two modes: FAST (no reasoning block; at
most one short persona-styled plan sentence before a command) and SLOW
(reasoning block with a hard ~150-token budget, serialized however the base
model's template does reasoning; ~2s at M4 Max decode speeds). Routing by
input event: action planning, goal changes, error recovery → SLOW; reactive
social chat, routine continuation → FAST. Three escalation overrides:
(a) any failed execution_result makes the next turn SLOW; (b) any ADR-0005
setter invocation makes the next turn SLOW; (c) the model may emit a
reserved escalation marker in a FAST turn, causing the loop to re-issue that
turn as SLOW. Log the mode, the trigger, and realized reasoning tokens on
every step.

**Consequences.** Experiment plan: two co-equal arms decided by the eval
battery — (A) event-routed FAST/SLOW; (B) always-SLOW at the same budget
(no router, no misrouting). If (B) is within noise on success and p95
latency holds, prefer (B) for simplicity. This is a hypothesis, revisited
with latency-vs-success eval data.
