# show-eval v0 — entertainment scorecard (design)

The capability battery measures whether the bot can play; this measures
whether the bot is worth watching. Scored during attended playtest sessions
(see roadmap); all metrics are operator-recorded in v0, judge-assisted later.

- Persona distinctiveness: blinded identification — given a 2-minute
  transcript with names stripped, can the operator (later: a judge model)
  name the persona? Target: near-100% for shipped personas.
- Interaction loop latency, three timestamps per intervention:
  request -> in-character acknowledgement; acknowledgement -> state applied
  (ADR-0005 setter); applied -> visibly changed behavior in-game.
- Intervention success rate: fraction of persona/goal changes that produce
  an observable, on-persona behavior change within N steps.
- Moments per hour: operator marks clip-worthy moments; separately marks
  intervention-to-payoff moments (a viewer action that visibly caused a
  memorable consequence — the core paid loop).
- Stuck rate: minutes per session spent visibly stuck/looping (ties the
  reliability work to the show: a stuck bot is dead air).

Show-event lineage: every intervention carries a correlation id linking
viewer request -> setter call -> next model turn -> gameplay consequence
(fields live in the future intervention event log, not in TrajectoryStep).
Without lineage, paid-interaction quality cannot be evaluated.
