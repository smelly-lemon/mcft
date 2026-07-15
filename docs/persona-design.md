# persona v1 — beyond voice cards (design)

The v0 persona schema (id, voice, chat_style, boundaries) ships this session
and stays frozen for the scaffold. It produces different prose, not
different play. Persona v1 adds fields that change BEHAVIOR, planned for the
show-prototype session:

- motivation: what this persona wants long-term (Sable: quiet competence;
  Jolt: spectacle; Herald: completed quests, ceremonially).
- strategy_bias: preferred approaches (Jolt rushes and improvises; Sable
  prepares and hedges; Herald follows declared quest order).
- risk_tolerance: guides combat/night/exploration choices.
- failure_react: on-persona failure behavior (Sable: flat acknowledgement,
  revised plan; Jolt: dramatic despair, instant re-hype; Herald: laments
  the setback of the quest).
- recurring_bits: catchphrases, rituals, running jokes — the hooks viewers
  subscribe for.
- continuity: what the persona remembers across sessions (grudges, projects,
  named places) — feeds the long-session memory backlog item.

Design constraints carried over from v0: the action contract stays
byte-identical across personas; behavior differences must come from goal
selection and style, never from breaking the command interface. Persona v1
fields are runtime config (ADR-0002: personality lives at runtime); organic
trajectories recorded under v1 personas are what teach behavioral variety.
