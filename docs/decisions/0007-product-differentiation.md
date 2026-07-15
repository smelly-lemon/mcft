# ADR-0007: Product differentiation

**Context.** Andy-4.2 — the Mindcraft community's free model — already
covers "a decent local model plays Minecraft" on the same base family,
framework, and SFT recipe this project uses. Rebuilding it better is not a
product.

**Decision.** What mcft deliberately inherits vs. bets on. Inherited
substrate (no differentiation claimed, none needed): Mindcraft framework,
Qwen-family base, trajectory SFT, GGUF/local serving. Product bets (no
incumbent exists for any of these): (1) the audience-steered persona show —
the Neuro-sama/TwitchCraft intersection nobody occupies in Minecraft;
(2) measured steerability — Andy's data already persona-conditions but
nobody has ever measured adherence; (3) measured reliability — no published
evals exist in this ecosystem; Andy-4.2 is a named eval baseline (pure
inference; its Andy-2.0 license permits this — training on its outputs stays
forbidden per ADR-0003, and its candid model-card failure list —
long-context repetition, precondition neglect, newAction collapse,
overthinking — is adopted as eval targets); (4) persona depth that changes
play, not just prose (docs/persona-design.md).

**Consequences.** Non-goal: beating Andy by reproducing its recipe with
better hygiene. Sequencing follows: the show prototype precedes training
(see the post-scaffold roadmap in kickoff_prompt.md).
