# Intent graph (goal + meaning layer) — design note, 2026-07-20

Proposal (Tim): link short- and long-term goals explicitly, add a meaning
layer ("why" each goal exists), make personality steering operate on the
why-layer, and store it all as a network data structure.

## Why this is grounded, not speculative

Every motivating failure is in our logs:

- **Sable 2026-07-20 (Y=6 incident)**: "collect cobblestone" lost its parent
  ("for the wall at the site, Y=85"); a blended coordinate survived because
  free-text journals carry no structural contradiction. With a graph, the
  parent node carries the anchor - corruption is detectable/rejectable.
- **Journal drift class**: model-written GOAL/PLAN text decays. Graph = code-
  owned; journal GOAL/SITE lines become *generated* from the graph.
- **Loop-breaking**: today we nudge "try something else"; with a graph the
  bot walks up one level and picks a sibling subgoal serving the same parent
  - a principled unstuck mechanism.
- **Cooperation**: Project Sid - role specialization requires awareness of
  others' goals. Shared graph -> partner's active path visible in one line.
- **Mission phases** (walls -> roof -> door -> farm) are already a goal chain
  hard-coded in a prompt string; this makes it live and mutable.

## Novelty (per 2026-07-20 validated landscape scan)

Adjacent prior art: VillagerAgent task DAGs (validated: reduces hallucination
vs free-form), HTN planning, Voyager curriculum, Generative Agents reflection
trees. NOT found anywhere: values-grounded why-layer as the persona-steering
mechanism, runtime-mutable as a (paid) steering surface, emitting
rationale-annotated trajectories as training data. The moat is the dataset +
product mechanic, not the data structure.

## What it buys the product

1. **Steering API**: steering = insert goal node / reweight value, every node
   provenance-tagged (`created_by: system|persona|operator|viewer`). The
   "tokens" mechanic gets a concrete surface.
2. **Stream overlay**: render the active path - "mining coal -> torches ->
   light the house -> because night is dangerous." The narrative is readable
   from state, not confabulated.
3. **Training data**: each TrajectoryStep logs its active goal path ->
   rationale-annotated SFT data, structurally faithful (unlike free-form CoT).
   Strongest differentiation vs Andy's dataset.

## Hard constraint (learned via memguard/journal drift)

**Code owns the graph; the model proposes ops.** Same discipline as the
command layer. Schema-validated ops; malformed ops rejected; graph never
serialized wholesale into the prompt.

## v1 data model (tree, not yet network)

```
IntentNode:
  id: short slug
  kind: value | goal | task
  title: short string
  why: rationale text on the edge to parent (one line)
  parent: node id (single parent in v1)
  status: active | done | blocked | abandoned
  owner: sable | jolt | shared
  anchor: optional (x,y,z) - inherited from nearest ancestor if absent
  created_by: system | persona | operator | viewer
  weight: float (values only: per-persona weights, e.g. sable.craftsmanship=0.8)
```

- Roots: persona value nodes + one shared mission root (the homestead).
- Anchors inherit downward -> a subgoal whose coords contradict its inherited
  anchor beyond tolerance is auto-flagged (kills the Y=59 blend class).

## v1 model interface

- **Read**: prompt section INTENT (~200 tokens): active leaf -> ancestor path
  with whys, up to 3 sibling alternatives, partner's active path (one line),
  top value weights.
- **Write** (new commands, validated like all commands):
  - `!goalDone(reason)`
  - `!goalAdd(parent_id, title, why)`
  - `!goalSwitch(node_id, why)`
- **Auto-ops by code**: loop-breaker v3 marks the active node `blocked` after
  repetition and presents siblings; siteguard checks action coords against
  inherited anchors; journal GOAL/SITE generated from graph each save.
- **Shared state**: one JSON file (or mindserver channel) with owner fields;
  duplicate-work detector flags two bots active on the same node.

## Metrics (battery meters to add)

- goal-path coherence: does the emitted command semantically match the active
  leaf (judge-scored on samples)
- orphan rate: % steps with no active node
- value consistency: judge - does behavior reflect declared value weights
- steering latency: op inserted -> first action serving it

## Sequencing

1. Clean run ships FIRST on the current scaffold (baseline era; do not block).
2. Intent-graph v1 = next scaffold epoch (new era tag for data comparability).
3. Battery calibration + bake-off run on v1 scaffold.
4. Teacher datagen AFTER v1 so the expensive teacher trajectories carry
   rationale annotations.
5. v2 (true network: multiple parents, causal edges, cross-bot dependency
   edges) only after v1 proves the model can drive the op interface.
