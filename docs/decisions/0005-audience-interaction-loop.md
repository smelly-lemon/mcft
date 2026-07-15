# ADR-0005: Audience interaction loop

**Context.** The product is a show that paying viewers can steer; that loop
must be auditable, safe, and prototyped before any money touches it.

**Decision.** The interaction loop is the product, not plumbing. Persona and
goal are runtime state, changed only through a single setter interface in
the bot loop; the full intervention lifecycle is: request → validation →
conflict policy (what wins when interventions collide or arrive mid-action)
→ application → in-character acknowledgement → duration/expiry → audit event
→ observable consequence. Every step logs persona_id and system_prompt_hash;
every intervention carries a correlation id (see docs/show-eval-v0.md
lineage). A payment system is just another caller of the setter — the
mock/local interaction loop is prototyped in attended sessions FIRST
(roadmap step 3); payments, platform integration, and monetization stay
behind the EULA gate.

**Consequences.** Interaction quality is measurable end-to-end before
monetization. Bot-hosting-as-a-service remains undecided pending research;
a fine-tuning-platform product is far future.
