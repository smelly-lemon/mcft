# ADR-0002: Capability in weights, personality at runtime

**Context.** Fine-tuning on one character's transcripts destroys
system-prompt steerability (persona collapse), and the product requires many
switchable personas on one model.

**Decision.** SFT data pairs each trajectory with varied persona system
prompts; the action-contract block is shared and byte-identical across
personas so steering never degrades the action interface. Behavioral
personality (goal selection, pacing) comes from organic per-persona
trajectories; synthetic chat-only rewrites are augmentation, not the source
of personality.

**Consequences.** Personas are config files, changeable without retraining.
This is a hypothesis validated by persona_adherence scores and per-persona
capability deltas, not a settled fact — revisit with eval data.
