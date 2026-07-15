# ADR-0006: Code execution and operational safety

**Context.** The bot executes model-generated code (newAction) 24/7; that is
an arbitrary-code-execution surface, independent of any payment features.

**Decision.** Sandboxed execution with a command allowlist, rate limits on
commands and chat output, a kill switch that halts the bot without touching
the server, credential isolation (the bot account holds no credentials
beyond its own login), and explicit server-owner consent are requirements
before unattended operation.

**Consequences.** No unattended 24/7 operation until all requirements are
met; attended sessions until then. Requirements are restated in the
Mindcraft integration README where the logger/bot work happens.
